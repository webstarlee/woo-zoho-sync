import os, json
from app.agents.zoho import ZohoAgent
from app.agents.postgres import PostgresAgent
from app.models.category import CategoryBase

async def create_category():
    count = 0
    total_count = 0
    while True:
        filename = f"categories/categories_level_{count}.json"
        if not os.path.exists(filename):
            break
        
        with open(filename, 'r') as f:
            categories = json.load(f)
            
        for category in categories:
            if category["woo_parent_id"] == 0:
                category_base = CategoryBase(
                    name=category["name"],
                    woo_id=category["woo_id"],
                    woo_parent_id=category["woo_parent_id"],
                    description=category["description"],
                    url=category["url"],
                    zoho_id=None,
                    zoho_parent_id="-1"
                )
                result = await ZohoAgent().create_category(category_base)
                if result.get("category"):
                    category_base.zoho_id = result['category']['category_id']
                    category_base.zoho_parent_id = result['category']['parent_category_id']
                    await PostgresAgent().insert_category(category_base)
                    print(f"Created category {category['name']} with id {category_base.zoho_id}")
                
                total_count += 1
            else:
                parent_category = await PostgresAgent().get_category_by_woo_id(category["woo_parent_id"])
                if parent_category:
                    category_base = CategoryBase(
                        name=category["name"],
                        woo_id=category["woo_id"],
                        woo_parent_id=category["woo_parent_id"],
                        description=category["description"],
                        url=category["url"],
                        zoho_id=None,
                        zoho_parent_id=parent_category.zoho_id
                    )
                    result = await ZohoAgent().create_category(category_base)
                    if result.get("category"):
                        category_base.zoho_id = result['category']['category_id']
                        category_base.zoho_parent_id = result['category']['parent_category_id']
                        await PostgresAgent().insert_category(category_base)
                        print(f"Created category {category['name']} with id {category_base.zoho_id} deep {count}")
                    total_count += 1
                else:
                    category_base = CategoryBase(
                        name=category["name"],
                        woo_id=category["woo_id"],
                        woo_parent_id=category["woo_parent_id"],
                        description=category["description"],
                        url=category["url"],
                        zoho_id=None,
                        zoho_parent_id="-1"
                    )
                    result = await ZohoAgent().create_category(category_base)
                    if result.get("category"):
                        category_base.zoho_id = result['category']['category_id']
                        category_base.zoho_parent_id = result['category']['parent_category_id']
                        await PostgresAgent().insert_category(category_base)
                        print(f"Created category {category['name']} with id {category_base.zoho_id}")
                    total_count += 1
            
            
        count += 1
        print(f"{count} - Total count: {total_count}")
    
    print(f"Total count: {total_count}")