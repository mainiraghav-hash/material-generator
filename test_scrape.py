from material_generator import real_scrape

materials = [
    "Aluminum 6061-T6",
    "Aluminum 7075-T6",
    "Aluminum 2024-T3",
    "Aluminum 5052-H32",
    "Aluminum 6063-T5",
    "Aluminum 3003-H14",
    "Aluminum 2014-T6",
    "Aluminum 5083-O",
    "Aluminum 7050-T7451",
    "Aluminum 6082-T6"
]

print("Testing MatWeb Scraper for 10 Aluminum Alloys...\n")

success_count = 0
for mat in materials:
    print(f"Scraping: {mat}...")
    result = real_scrape(mat)
    if result:
        print(f"  [SUCCESS] Name: {result['name']}")
        print(f"            Density: {result['density']} kg/m³")
        print(f"            Young's Mod: {result['youngs_mod'] / 1e9:.2f} GPa")
        print(f"            Poisson's: {result['poisson']}")
        print(f"            Yield Str: {result['yield_str'] / 1e6:.2f} MPa")
        print(f"            Source: {result['source_url']}")
        success_count += 1
    else:
        print(f"  [FAILED] Could not retrieve data for {mat}")
        
print(f"\nFinal Score: {success_count}/10")
