from flask import Blueprint, jsonify
from database import get_connection

search_bp = Blueprint('search', __name__)

@search_bp.route('/api/search/<keyword>', methods=['GET'])
def search(keyword):
    conn = get_connection()
    cursor = conn.cursor()

    # Search afternic_domains
    cursor.execute("""
    SELECT domain, price, category, is_fast_transfer
    FROM afternic_domains
    WHERE LOWER(domain) LIKE %s
    LIMIT 50
""", (f'%{keyword.lower()}%',))

    results = cursor.fetchall()

    if not results:
        cursor.close()
        conn.close()
        return jsonify({"message": "No results found", "keyword": keyword}), 404

    # Get all domain names first
    domain_names = []
    for row in results:
        parts = row[0].rsplit('.', 1)
        domain_name = parts[0] if len(parts) == 2 else row[0]
        domain_names.append(domain_name.lower())

    # ONE single ICANN query - just count per domain
    cursor.execute("""
        SELECT 
            LOWER(SPLIT_PART(domain, '.', 1)) as name,
            STRING_AGG(tld, ', ') as tlds,
            COUNT(*) as tld_count
        FROM icann_domains
        WHERE LOWER(SPLIT_PART(domain, '.', 1)) = ANY(%s)
        GROUP BY LOWER(SPLIT_PART(domain, '.', 1))
    """, (domain_names,))

    icann_rows = cursor.fetchall()

    # Group ICANN results
    icann_map = {}
    for icann_row in icann_rows:
        icann_map[icann_row[0]] = {
            "tlds": icann_row[1],
            "count": icann_row[2]
        }

    # Build response
    response = []
    for row in results:
        domain_full = row[0]
        price = row[1]
        category = row[2]
        is_fast_transfer = row[3]

        parts = domain_full.rsplit('.', 1)
        domain_name = parts[0] if len(parts) == 2 else domain_full
        domain_extension = parts[1] if len(parts) == 2 else ''

        name_length = len(domain_name)
        has_hyphen = '-' in domain_name
        has_digit = any(c.isdigit() for c in domain_name)

        icann_data = icann_map.get(domain_name.lower(), {"tlds": "", "count": 0})

        response.append({
            "root_domain": domain_full,
            "domain_name": domain_name,
            "domain_extension": domain_extension,
            "price": price,
            "category": category,
            "is_fast_transfer": is_fast_transfer,
            "domain_details": {
                "name_length": name_length,
                "has_hyphen": has_hyphen,
                "has_digit": has_digit,
                "tld_availability": {
                    "registered_gtlds": icann_data["tlds"],
                    "registered_gtld_count": icann_data["count"]
                }
            }
        })

    cursor.close()
    conn.close()

    return jsonify(response)