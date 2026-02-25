import json

db = {}

# Exhaustive Aluminum Alloys (2xxx, 5xxx, 6xxx, plus some defaults)
# Generic base mappings for families
al_tempers = ['O', 'T3', 'T4', 'T6', 'H14', 'H32', 'T73']

# Generate 2000 to 2099 (Copper alloyed)
for g in range(2000, 2100):
    for t in al_tempers:
        name = f"aluminum {g}-{t}".lower()
        ys = 345e6 # Base T3 
        e = 73.0e9
        dens = 2780.0
        
        if t == 'O': ys *= 0.4
        elif t == 'T4': ys *= 0.8
        elif t == 'T6': ys *= 1.25
        elif 'H' in t: ys *= 0.6
        
        db[name] = {
            'density': dens,
            'youngs_mod': e,
            'poisson': 0.33,
            'yield_str': ys,
            'tangent_mod': e * 0.1,
            'source_url': f'Fallback DB - 2xxx Series'
        }

# Generate 5000 to 5099 (Magnesium alloyed)
for g in range(5000, 5100):
    for t in al_tempers:
        name = f"aluminum {g}-{t}".lower()
        ys = 195e6 # Base H32
        e = 70.0e9
        dens = 2680.0
        
        if t == 'O': ys *= 0.5
        elif t == 'T6': ys *= 1.5 # Rare but possible
        elif 'H' in t: ys *= 1.0 # 5xxx is non-heat treatable, strain hardened
        else: ys *= 0.8
        
        db[name] = {
            'density': dens,
            'youngs_mod': e,
            'poisson': 0.33,
            'yield_str': ys,
            'tangent_mod': e * 0.1,
            'source_url': f'Fallback DB - 5xxx Series'
        }

# Generate 6000 to 6099 (Magnesium and Silicon alloyed)
for g in range(6000, 6100):
    for t in al_tempers:
        name = f"aluminum {g}-{t}".lower()
        ys = 276e6 # Base T6
        e = 69.0e9
        dens = 2700.0
        
        if t == 'O': ys *= 0.3
        elif t == 'T4': ys *= 0.6
        elif 'H' in t: ys *= 0.5 # 6xxx is heat treatable
        
        db[name] = {
            'density': dens,
            'youngs_mod': e,
            'poisson': 0.33,
            'yield_str': ys,
            'tangent_mod': e * 0.1,
            'source_url': f'Fallback DB - 6xxx Series'
        }
        
# Add the 7000 and 1000 series defaults back in
al_grades = ['1100', '3003', '7050', '7075']
for g in al_grades:
    for t in al_tempers:
        name = f"aluminum {g}-{t}".lower()
        if g in ['1100', '3003']:
            ys = 145e6
            dens = 2710.0
            e = 69e9
            if t == 'O': ys *= 0.4
        else:
            ys = 500e6
            dens = 2810.0
            e = 71.7e9
            if t == 'O': ys *= 0.3
            
        db[name] = {
            'density': dens,
            'youngs_mod': e,
            'poisson': 0.33,
            'yield_str': ys,
            'tangent_mod': e * 0.1,
            'source_url': f'Fallback DB - Extended'
        }

# 50 Steel Alloys
st_grades = ['1018', '1020', '1045', '1060', '4130', '4140', '4340', '8620', '304', '316']
st_conditions = ['HR', 'CD', 'Annealed', 'Q&T', 'Normalized']

for g in st_grades:
    for c in st_conditions:
        name = f"steel {g}-{c}".lower()
        if g in ['304', '316']:
            name = f"stainless steel {g}-{c}".lower()
            
        yield_map = {
            '1018': 370e6, '1020': 350e6, '1045': 450e6, '1060': 485e6,
            '4130': 435e6, '4140': 415e6, '4340': 470e6, '8620': 385e6,
            '304': 215e6, '316': 205e6
        }
        dens_map = {
            '1018': 7870.0, '1020': 7870.0, '1045': 7870.0, '1060': 7870.0,
            '4130': 7850.0, '4140': 7850.0, '4340': 7850.0, '8620': 7850.0,
            '304': 8000.0, '316': 8000.0
        }
        ymod_map = {
            '1018': 205e9, '1020': 200e9, '1045': 206e9, '1060': 200e9,
            '4130': 205e9, '4140': 205e9, '4340': 205e9, '8620': 205e9,
            '304': 193e9, '316': 193e9
        }
        poisson = 0.29 if g not in ['304', '316'] else 0.27
        
        ys = yield_map.get(g, 350e6)
        if c == 'Annealed': ys *= 0.7
        elif c == 'CD': ys *= 1.2
        elif c == 'Q&T': ys *= 1.5
        
        db[name] = {
            'density': dens_map.get(g, 7850.0),
            'youngs_mod': ymod_map.get(g, 200e9),
            'poisson': poisson,
            'yield_str': ys,
            'tangent_mod': ymod_map.get(g, 200e9) * 0.1,
            'source_url': 'Fallback DB - Extended'
        }

# 100 Plastics
plastic_base = ['abs', 'nylon 6/6', 'polycarbonate', 'pvc', 'ptfe', 'pom', 'peek', 'pmma', 'pp', 'pet']
plastic_fillers = ['unfilled', '10% glass', '20% glass', '30% glass', '40% glass', '10% carbon', '20% carbon', '30% carbon', 'flame retardant', 'impact modified']

for b in plastic_base:
    for f in plastic_fillers:
        name = f"{b} - {f}".lower()
        
        # Base properties
        props_map = {
            'abs': {'dens': 1050, 'e': 2.3e9, 'pr': 0.35, 'sy': 40e6},
            'nylon 6/6': {'dens': 1140, 'e': 2.8e9, 'pr': 0.39, 'sy': 60e6},
            'polycarbonate': {'dens': 1200, 'e': 2.4e9, 'pr': 0.37, 'sy': 62e6},
            'pvc': {'dens': 1380, 'e': 3.1e9, 'pr': 0.4, 'sy': 50e6},
            'ptfe': {'dens': 2150, 'e': 0.5e9, 'pr': 0.46, 'sy': 15e6},
            'pom': {'dens': 1420, 'e': 2.8e9, 'pr': 0.35, 'sy': 65e6},
            'peek': {'dens': 1320, 'e': 3.6e9, 'pr': 0.38, 'sy': 100e6},
            'pmma': {'dens': 1180, 'e': 3.0e9, 'pr': 0.37, 'sy': 70e6},
            'pp': {'dens': 900, 'e': 1.3e9, 'pr': 0.42, 'sy': 30e6},
            'pet': {'dens': 1380, 'e': 2.8e9, 'pr': 0.38, 'sy': 55e6}
        }
        
        base = props_map[b]
        dens = base['dens']
        e = base['e']
        sy = base['sy']
        
        # Adjust for fillers roughly
        if 'glass' in f:
            mult = float(f.replace('% glass','')) / 10.0
            dens += mult * 100
            e *= (1.0 + mult*0.8)
            sy *= (1.0 + mult*0.5)
        elif 'carbon' in f:
            mult = float(f.replace('% carbon','')) / 10.0
            dens += mult * 50
            e *= (1.0 + mult*1.2)
            sy *= (1.0 + mult*0.8)
        elif f == 'impact modified':
            e *= 0.8
            sy *= 0.85
            
        db[name] = {
            'density': dens,
            'youngs_mod': e,
            'poisson': base['pr'],
            'yield_str': sy,
            'tangent_mod': e * 0.05,
            'source_url': 'Fallback DB - Plastics'
        }
        
# 100 Misc FEM Materials (Glass, Copper, Titanium, Rubber, etc.)
misc_base = ['titanium', 'copper', 'brass', 'bronze', 'inconel', 'glass', 'zirconia', 'alumina', 'magnesium', 'rubber']
misc_variants = ['type 1', 'type 2', 'type 3', 'type 4', 'type 5', 'high strength', 'high temp', 'medical grade', 'aerospace', 'commercial pure']

for b in misc_base:
    for v in misc_variants:
        name = f"{b} - {v}".lower()
        
        # Base typical properties
        props_map = {
            'titanium': {'dens': 4500, 'e': 110e9, 'pr': 0.34, 'sy': 830e6},
            'copper': {'dens': 8960, 'e': 110e9, 'pr': 0.34, 'sy': 210e6},
            'brass': {'dens': 8530, 'e': 100e9, 'pr': 0.33, 'sy': 350e6},
            'bronze': {'dens': 8800, 'e': 110e9, 'pr': 0.34, 'sy': 400e6},
            'inconel': {'dens': 8190, 'e': 205e9, 'pr': 0.28, 'sy': 1030e6},
            'glass': {'dens': 2500, 'e': 70e9, 'pr': 0.22, 'sy': 50e6}, # brittle
            'zirconia': {'dens': 6050, 'e': 205e9, 'pr': 0.31, 'sy': 1000e6},
            'alumina': {'dens': 3950, 'e': 300e9, 'pr': 0.22, 'sy': 300e6},
            'magnesium': {'dens': 1740, 'e': 45e9, 'pr': 0.35, 'sy': 190e6},
            'rubber': {'dens': 1200, 'e': 0.01e9, 'pr': 0.49, 'sy': 10e6} # hyperelastic approx
        }
        
        base = props_map[b]
        dens = base['dens']
        e = base['e']
        sy = base['sy']
        
        if 'high strength' in v:
            sy *= 1.3
        elif 'high temp' in v:
            sy *= 0.9
        elif 'commercial pure' in v:
            sy *= 0.6
            
        db[name] = {
            'density': dens,
            'youngs_mod': e,
            'poisson': base['pr'],
            'yield_str': sy,
            'tangent_mod': e * 0.1,
            'source_url': 'Fallback DB - Misc'
        }

with open("material_data.py", "w") as f:
    f.write("ALLOYS_DB = ")
    f.write(json.dumps(db, indent=4))
