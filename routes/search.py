from flask import Blueprint, jsonify, request
from database import get_connection

search_bp = Blueprint('search', __name__)

@search_bp.route('/api/search/<keyword>', methods=['GET'])
def search(keyword):
    conn = get_connection()
    cursor = conn.cursor()

    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)
    offset = (page - 1) * per_page

    # Get total count first
    cursor.execute("""
        SELECT COUNT(*) FROM afternic_domains
        WHERE LOWER(domain) LIKE %s
    """, (f'%{keyword.lower()}%',))
    
    total_count = cursor.fetchone()[0]

    # Search afternic_domains with pagination
    cursor.execute("""
        SELECT domain, price, category, is_fast_transfer
        FROM afternic_domains
        WHERE LOWER(domain) LIKE %s
        LIMIT %s OFFSET %s
    """, (f'%{keyword.lower()}%', per_page, offset))

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

    # ONE single ICANN query
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
    results_list = []
    for row in results:
        domain_full = row[0]
        price = row[1]
        is_fast_transfer = row[3]

        parts = domain_full.rsplit('.', 1)
        domain_name = parts[0] if len(parts) == 2 else domain_full
        domain_extension = parts[1] if len(parts) == 2 else ''

        name_length = len(domain_name)
        has_hyphen = '-' in domain_name
        has_digit = any(c.isdigit() for c in domain_name)

        icann_data = icann_map.get(domain_name.lower(), {"tlds": "", "count": 0})

        results_list.append({
            "root_domain": domain_full,
            "domain_name": domain_name,
            "domain_extension": domain_extension,
            "price": price,
            "fast_transfer": is_fast_transfer,
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

    # Calculate pagination
    last_page = (total_count + per_page - 1) // per_page

    cursor.close()
    conn.close()

    return jsonify({
        "total_count": total_count,
        "current_page_count": len(results_list),
        "current_page": page,
        "last_page": last_page,
        "per_page": per_page,
        "results": results_list
    })