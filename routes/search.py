from flask import Blueprint, jsonify, request
from database import get_connection

search_bp = Blueprint('search', __name__)

@search_bp.route('/api/search/<keyword>', methods=['GET'])
def search(keyword):
    conn = get_connection()
    cursor = conn.cursor()

    # Minimum keyword length check
   

    # Parameters
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 100, type=int)
    is_prefix = request.args.get('is_prefix', 0, type=int)
    is_suffix = request.args.get('is_suffix', 0, type=int)
    offset = (page - 1) * limit

    # Build search pattern based on parameters
    if is_prefix == 1:
        pattern = f'{keyword.lower()}%'
    elif is_suffix == 1:
        pattern = f'%{keyword.lower()}.%'
    else:
        pattern = f'%{keyword.lower()}%'

        

    # Get results AND total count in ONE query!
    cursor.execute("""
        SELECT domain, price, category, is_fast_transfer,
               COUNT(*) OVER() as total_count
        FROM afternic_domains
        WHERE LOWER(domain) LIKE %s
        LIMIT %s OFFSET %s
    """, (pattern, limit, offset))

    results = cursor.fetchall()

    if not results:
        cursor.close()
        conn.close()
        return jsonify({
            "status": "ok",
            "total_count": 0,
            "current_page_count": 0,
            "current_page": page,
            "last_page": 0,
            "per_page": limit,
            "domains": []
        })
    
    

    # Get total count from first row
    total_count = results[0][4]

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
            STRING_AGG(DISTINCT tld, ', ') as tlds,
            COUNT(DISTINCT tld) as tld_count
        FROM icann_domains
        WHERE LOWER(SPLIT_PART(domain, '.', 1)) = ANY(%s)
        GROUP BY LOWER(SPLIT_PART(domain, '.', 1))
    """, (domain_names,))

    icann_rows = cursor.fetchall()

    # Group ICANN results
    icann_map = {}
    for icann_row in icann_rows:
        name = icann_row[0]
        tlds = list(set(icann_row[1].split(', ')))
        count = len(tlds)
        icann_map[name] = {
            "tlds": ", ".join(sorted(tlds)),
            "count": count
        }

    # Build response
    domains_list = []
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

        domains_list.append({
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
    last_page = (total_count + limit - 1) // limit

    cursor.close()
    conn.close()

    return jsonify({
        "status": "ok",
        "total_count": total_count,
        "current_page_count": len(domains_list),
        "current_page": page,
        "last_page": last_page,
        "per_page": limit,
        "domains": domains_list
    })




    