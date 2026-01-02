# Property Data Organization Overview

## 📁 Folder Structure

```
data/raw/properties/
├── all/                           # Mixed property types
│   └── README.md                  # Guidelines for mixed data
├── residential/                   # Residential properties
│   ├── flat/                      # Apartments & flats
│   │   ├── bangalore-residential-apartment.csv
│   │   ├── bangalore-residential-apartment.json
│   │   ├── bangalore-residential-apartment-rent.csv
│   │   └── bangalore-residential-apartment-rent.json
│   ├── house/                     # Independent houses
│   │   ├── bangalore-residential-house.csv
│   │   ├── bangalore-residential-house.json
│   │   ├── bangalore-residential-house-rent.csv
│   │   └── bangalore-residential-house-rent.json
│   ├── villa/                     # Luxury villas (empty)
│   ├── plot/                      # Residential plots
│   │   ├── bangalore-residential-plot.csv
│   │   └── bangalore-residential-plot.json
│   ├── 1bhk/                      # 1 Bedroom (empty)
│   ├── 2bhk/                      # 2 Bedroom (empty)
│   ├── 3bhk/                      # 3 Bedroom (empty)
│   ├── 4bhk/                      # 4 Bedroom (empty)
│   ├── 5bhk/                      # 5 Bedroom (empty)
│   ├── 5plus-bhk/                 # 5+ Bedroom (empty)
│   ├── README.md                  # Residential guidelines
│   └── INDEX.md                   # File index
├── commercial/                    # Commercial properties
│   ├── office-space/              # Office spaces
│   │   ├── bangalore-commercial-officespace.csv
│   │   └── bangalore-commercial-officespace.json
│   ├── shop-showroom/             # Retail shops & showrooms
│   │   ├── bangalore-commercial-shop-rent.csv
│   │   └── bangalore-commercial-shop-rent.json
│   ├── commercial-land/           # Commercial plots
│   │   ├── bangalore-commercial-land.csv
│   │   └── bangalore-commercial-land.json
│   ├── warehouse-godown/          # Storage facilities
│   │   ├── bangalore-commercial-warehouse.csv
│   │   └── bangalore-commercial-warehouse.json
│   ├── industrial-building/       # Industrial buildings
│   │   ├── bangalore-commercial-industrialbuilding.csv
│   │   └── bangalore-commercial-industrialbuilding.json
│   ├── industrial-shed/           # Industrial sheds
│   │   ├── bangalore-commercial-industrialshed.csv
│   │   └── bangalore-commercial-industrialshed.json
│   ├── README.md                  # Commercial guidelines
│   └── INDEX.md                   # File index
├── other/                         # Other property types
│   ├── agricultural-land/         # Agricultural & farm land
│   │   ├── bangalore-agriculturalland.csv
│   │   └── bangalore-agriculturalland.json
│   ├── farm-house/                # Farm houses & weekend homes
│   │   ├── bangalore-farmhouse.csv
│   │   └── bangalore-farmhouse.json
│   ├── README.md                  # Other property guidelines
│   └── INDEX.md                   # File index
└── OVERVIEW.md                    # This file
```

## 📊 Data Summary

### Residential Properties
- **Apartments**: 4 files (2 sale + 2 rent)
- **Houses**: 4 files (2 sale + 2 rent)
- **Plots**: 2 files (sale only)
- **Total**: 10 files covering Bangalore residential market

### Commercial Properties
- **Office Spaces**: 2 files
- **Shop/Showroom**: 2 files (rent data)
- **Commercial Land**: 2 files
- **Warehouse/Godown**: 2 files
- **Industrial Building**: 2 files
- **Industrial Shed**: 2 files
- **Total**: 12 files covering commercial segments

### Other Properties
- **Agricultural Land**: 2 files
- **Farm House**: 2 files
- **Total**: 4 files for special properties

## 🚀 How to Use

### 1. **Load All Properties**
```powershell
.\.venv\Scripts\python.exe backend\services\run_etl.py --folder properties --compute-spatial
```

### 2. **Load Specific Type**
```powershell
# Load only residential flats
.\.venv\Scripts\python.exe backend\services\run_etl.py --folder properties/residential/flat

# Load only commercial properties
.\.venv\Scripts\python.exe backend\services\run_etl.py --folder properties/commercial
```

### 3. **Add New Data**
- Place CSV/JSON files in appropriate sub-folder
- Follow column structure in README files
- Include latitude/longitude for mapping

## 📋 Required Columns

For all property types:
- `name` - Property name/title
- `property_type` - Type (flat, house, villa, etc.)
- `description` - Property description
- `price` - Price in INR
- `area_sqft` - Area in square feet
- `location` - Address/location text
- `latitude` - Geographic coordinate
- `longitude` - Geographic coordinate
- `city` - City name (e.g., "Bangalore")
- `locality` - Area/locality (e.g., "Whitefield")
- `bedrooms` - Number of bedrooms (if applicable)
- `bathrooms` - Number of bathrooms (if applicable)
- `built_year` - Year built
- `parking_spaces` - Number of parking spaces
- `balconies` - Number of balconies
- `floor` - Floor number
- `total_floors` - Total floors in building
- `age_years` - Property age
- `transaction_type` - Sale/Rent/Lease
- `price_per_sqft` - Price per square foot
- `listed_date` - Date listed
- `days_on_market` - Days since listing

## 🎯 Benefits of This Organization

1. **Easy Navigation**: Clear categorization by property type
2. **Targeted Analysis**: Load specific property segments
3. **Scalable Structure**: Add new types easily
4. **AI-Ready**: Organized for ML model training
5. **Spatial Analysis**: Ready for GIS integration
6. **Market Segmentation**: Separate residential/commercial/other

## 📈 Next Steps

1. Add BHK-specific data to 1bhk, 2bhk, etc. folders
2. Include more villa listings in villa folder
3. Add rental data for commercial land
4. Integrate with GIS for location-based analysis
5. Use for training property recommendation models
