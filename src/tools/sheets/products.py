"""Tools para productos con búsqueda inteligente."""

from typing import Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import structlog

from .client import get_client
from src.schemas.product import Product

logger = structlog.get_logger()

# Palabras clave para identificar tipo de mascota en productos
PET_KEYWORDS = {
    "perro": ["perro", "perros", "can", "canino", "canine", "dog", "dogs", "cachorro", "cachorros", "puppy", "puppies", "lomito"],
    "gato": ["gato", "gatos", "felino", "feline", "cat", "cats", "gatito", "gatitos", "michi", "minino", "kitten"],
    "hamster": ["hamster", "hámster", "roedor", "roedores", "cobayo", "cobaya", "cuyo", "jerbo", "chinchilla", "raton", "ratón"],
    "conejo": ["conejo", "conejos", "conejito", "bunny", "rabbit"],
    "ave": ["ave", "aves", "pajaro", "pájaro", "perico", "periquito", "canario", "loro", "bird", "birds"],
    "pez": ["pez", "peces", "acuario", "pecera", "goldfish", "betta", "fish", "tropical"],
}

# Alias de mascotas (para normalizar lo que dice el usuario)
PET_ALIASES = {
    "roedor": "hamster",
    "cobayo": "hamster",
    "cuyo": "hamster",
    "chinchilla": "hamster",
    "conejito": "conejo",
    "bunny": "conejo",
    "pajaro": "ave",
    "pájaro": "ave",
    "loro": "ave",
    "periquito": "ave",
    "canario": "ave",
    "acuario": "pez",
    "pecera": "pez",
}

# Marcas conocidas por tipo de mascota (para cuando la descripción no lo indica)
PET_BRANDS = {
    "perro": ["pro plan", "royal canin", "pedigree", "purina", "eukanuba", "hills", "diamond",
              "taste of the wild", "orijen", "acana", "blue buffalo", "instinct", "kong",
              "nufit", "nucan", "ganador", "champ", "optimo", "dog chow"],
    "gato": ["whiskas", "felix", "sheba", "fancy feast", "friskies", "kit kat", "mirringo", "cat chow"],
    "hamster": ["vitakraft", "versele-laga", "versele", "living world", "kaytee", "oxbow", "supreme", "tiny friends"],
    "conejo": ["vitakraft", "versele-laga", "versele", "oxbow", "kaytee", "living world", "supreme"],
    "ave": ["vitakraft", "kaytee", "zupreem", "versele-laga", "versele", "living world"],
    "pez": ["tetra", "sera", "api", "fluval", "aqueon", "hikari"],
}

# Palabras clave para tipo de producto
PRODUCT_TYPE_KEYWORDS = {
    "comida": ["alimento", "croqueta", "croquetas", "comida", "food", "pienso", "nutricion"],
    "snack": ["snack", "snacks", "premio", "premios", "golosina", "treat", "treats", "botanita"],
    "juguete": ["juguete", "juguetes", "pelota", "toy", "toys", "mordedor"],
    "higiene": ["shampoo", "jabon", "limpieza", "higiene", "baño", "cepillo"],
    "accesorio": ["collar", "correa", "plato", "comedero", "bebedero", "cama", "casa"],
    "arena": ["arena", "arenero", "litter"],
    "salud": ["vitamina", "suplemento", "medicina", "antipulgas", "desparasitante"],
}


class ProductSearchInput(BaseModel):
    """Input para buscar productos."""

    query: str = Field(description="Término de búsqueda (nombre, categoría, marca)")
    max_results: int = Field(default=5, description="Número máximo de resultados")
    pet_type: Optional[str] = Field(default=None, description="Tipo de mascota (perro, gato, etc.)")


@tool(args_schema=ProductSearchInput)
def search_products(query: str, max_results: int = 5, pet_type: Optional[str] = None) -> list[dict]:
    """
    Busca productos en el catálogo de Animalicha con filtrado inteligente.

    Args:
        query: Término de búsqueda (nombre del producto, marca, categoría)
        max_results: Máximo de resultados a devolver
        pet_type: Filtrar por tipo de mascota (perro, gato, etc.)

    Returns:
        Lista de productos encontrados con: nombre, precio, stock, descripción
    """
    try:
        client = get_client()
        all_products = client.get_all_as_dicts()

        if not all_products:
            logger.warning("No products found in sheet")
            return []

        # Preparar búsqueda - expandir sinónimos
        query_lower = query.lower().strip()

        # Expandir la query con sinónimos de tipo de producto
        expanded_query_words = set()
        for word in query_lower.split():
            if len(word) > 2:
                expanded_query_words.add(word)
                # Agregar sinónimos
                for product_type, synonyms in PRODUCT_TYPE_KEYWORDS.items():
                    if word in synonyms or word == product_type:
                        expanded_query_words.update(synonyms)

        query_words = list(expanded_query_words)

        # Normalizar tipo de mascota (por si el usuario dice "roedor" en vez de "hamster")
        normalized_pet_type = pet_type.lower() if pet_type else None
        if normalized_pet_type and normalized_pet_type in PET_ALIASES:
            normalized_pet_type = PET_ALIASES[normalized_pet_type]

        # Obtener palabras clave de la mascota
        pet_filter_words = PET_KEYWORDS.get(normalized_pet_type, []) if normalized_pet_type else []
        pet_brands = PET_BRANDS.get(normalized_pet_type, []) if normalized_pet_type else []

        scored_results = []

        for row in all_products:
            # Construir texto de búsqueda
            descripcion = str(row.get("Descripcion", "")).lower()
            marca = str(row.get("Marca", "")).lower()
            familia = str(row.get("Familia", "")).lower()
            linea = str(row.get("linea", "")).lower()
            clave = str(row.get("Clave", "")).lower()

            search_text = f"{descripcion} {marca} {familia} {linea} {clave}"

            # ============================================
            # FILTRO POR MASCOTA (flexible)
            # ============================================
            is_for_pet = False
            is_for_other_pet = False

            if normalized_pet_type:
                # Verificar si tiene palabras de la mascota correcta
                is_for_pet = any(pw in search_text for pw in pet_filter_words)

                # Verificar si es de una marca conocida para esa mascota
                if not is_for_pet and pet_brands:
                    is_for_pet = any(pb in marca for pb in pet_brands)

                # Verificar si es de OTRA mascota (más estricto)
                for other_pet, other_words in PET_KEYWORDS.items():
                    if other_pet != normalized_pet_type:
                        if any(ow in search_text for ow in other_words):
                            is_for_other_pet = True
                            break

                # También verificar marcas de otras mascotas
                if not is_for_other_pet:
                    for other_pet, other_brands in PET_BRANDS.items():
                        if other_pet != normalized_pet_type:
                            if any(ob in marca for ob in other_brands):
                                is_for_other_pet = True
                                break

                # Si es claramente de otra mascota, SALTAR (filtro estricto)
                if is_for_other_pet and not is_for_pet:
                    continue

            # ============================================
            # BÚSQUEDA CON SCORING
            # ============================================
            score = 0

            # Coincidencia exacta de la query original
            if query_lower in search_text:
                score += 100

            # Contar coincidencias de palabras expandidas
            matching_words = sum(1 for word in query_words if word in search_text)

            # Si no hay coincidencias, saltar
            if matching_words == 0:
                continue

            # Score basado en coincidencias
            score += matching_words * 20

            # Bonus por coincidencia en descripción
            if any(word in descripcion for word in query_words):
                score += 30

            # Bonus si es de la mascota correcta
            if normalized_pet_type and is_for_pet:
                score += 50

            # Bonus si es marca conocida para esa mascota
            if pet_brands and any(pb in marca for pb in pet_brands):
                score += 40

            # Penalización FUERTE si es de otra mascota pero pasó el filtro inicial
            if is_for_other_pet:
                score -= 100

            # Crear producto normalizado
            product = {
                "id": row.get("Clave", ""),
                "name": row.get("Descripcion", ""),
                "category": row.get("Familia", ""),
                "brand": row.get("Marca", ""),
                "price": _parse_price(row.get("Precio Publico", "0")),
                "stock": 999,
                "description": f"{row.get('linea', '')} - {row.get('Marca', '')}",
                "unit": row.get("Unidad", "PZ"),
                "barcode": row.get("Codigo de barras", ""),
            }

            scored_results.append((score, product))

        # Ordenar por score descendente
        scored_results.sort(key=lambda x: x[0], reverse=True)
        results = [product for score, product in scored_results]

        logger.info(
            "Product search completed",
            query=query,
            pet_type=pet_type,
            results_count=len(results),
            top_scores=[s for s, _ in scored_results[:3]] if scored_results else [],
        )

        return results[:max_results]

    except Exception as e:
        logger.error("Error searching products", query=query, error=str(e))
        return []


@tool
def get_product_by_id(product_id: str) -> Optional[dict]:
    """
    Obtiene un producto específico por su ID o SKU.

    Args:
        product_id: ID o SKU del producto

    Returns:
        Diccionario con los datos del producto o None si no existe
    """
    try:
        client = get_client()
        all_products = client.get_all_as_dicts()

        for row in all_products:
            if row.get("Clave") == product_id or row.get("Codigo de barras") == product_id:
                return {
                    "id": row.get("Clave", ""),
                    "name": row.get("Descripcion", ""),
                    "category": row.get("Familia", ""),
                    "brand": row.get("Marca", ""),
                    "price": _parse_price(row.get("Precio Publico", "0")),
                    "stock": 999,
                    "description": f"{row.get('linea', '')} - {row.get('Marca', '')}",
                    "unit": row.get("Unidad", "PZ"),
                    "barcode": row.get("Codigo de barras", ""),
                }

        return None

    except Exception as e:
        logger.error("Error getting product", product_id=product_id, error=str(e))
        return None


@tool
def get_products_by_category(category: str, max_results: int = 10, pet_type: Optional[str] = None) -> list[dict]:
    """
    Obtiene productos de una categoría específica.

    Args:
        category: Categoría a buscar (alimento, snacks, juguetes, etc.)
        max_results: Máximo de resultados
        pet_type: Filtrar por tipo de mascota

    Returns:
        Lista de productos de esa categoría
    """
    try:
        client = get_client()
        all_products = client.get_all_as_dicts()

        category_lower = category.lower()
        pet_filter_words = PET_KEYWORDS.get(pet_type.lower(), []) if pet_type else []

        results = []

        for row in all_products:
            product_category = str(row.get("Familia", "")).lower()
            product_line = str(row.get("linea", "")).lower()
            search_text = f"{product_category} {product_line} {str(row.get('Descripcion', '')).lower()}"

            # Verificar categoría
            if category_lower not in product_category and category_lower not in product_line:
                continue

            # Filtrar por mascota si se especificó
            if pet_type and pet_filter_words:
                if not any(pw in search_text for pw in pet_filter_words):
                    continue

            results.append({
                "id": row.get("Clave", ""),
                "name": row.get("Descripcion", ""),
                "category": row.get("Familia", ""),
                "brand": row.get("Marca", ""),
                "price": _parse_price(row.get("Precio Publico", "0")),
                "stock": 999,
                "unit": row.get("Unidad", "PZ"),
            })

        return results[:max_results]

    except Exception as e:
        logger.error("Error getting products by category", category=category, error=str(e))
        return []


def _parse_price(value: str) -> float:
    """Parsea un precio a float."""
    try:
        clean = str(value).replace("$", "").replace(",", "").strip()
        return float(clean) if clean else 0.0
    except (ValueError, TypeError):
        return 0.0


def _parse_int(value: str) -> int:
    """Parsea un entero."""
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return 0
