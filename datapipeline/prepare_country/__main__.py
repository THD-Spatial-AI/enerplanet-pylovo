#!/usr/bin/env python3
"""
Unified country data preparation runner.

Usage:
    python -m datapipeline.prepare_country <country>
    
Examples:
    python -m datapipeline.prepare_country netherlands
    python -m datapipeline.prepare_country austria
    python -m datapipeline.prepare_country france
"""

import sys
import importlib

# All supported European countries
SUPPORTED_COUNTRIES = {
    # Western Europe
    'belgium': 'belgium',
    'france': 'france',
    'ireland': 'ireland',
    'luxembourg': 'luxembourg',
    'netherlands': 'netherlands',

    # Central Europe
    'austria': 'austria',
    'czech_republic': 'czech_republic',
    'germany': 'germany',
    'hungary': 'hungary',
    'liechtenstein': 'liechtenstein',
    'poland': 'poland',
    'slovakia': 'slovakia',
    'slovenia': 'slovenia',
    'switzerland': 'switzerland',

    # Northern Europe
    'denmark': 'denmark',
    'estonia': 'estonia',
    'finland': 'finland',
    'iceland': 'iceland',
    'latvia': 'latvia',
    'lithuania': 'lithuania',
    'norway': 'norway',
    'sweden': 'sweden',

    # Southern Europe
    'croatia': 'croatia',
    'cyprus': 'cyprus',
    'greece': 'greece',
    'italy': 'italy',
    'malta': 'malta',
    'portugal': 'portugal',
    'spain': 'spain',

    # Southeast Europe
    'bulgaria': 'bulgaria',
    'north_macedonia': 'north_macedonia',
    'romania': 'romania',
    'serbia': 'serbia',
    'turkey': 'turkey',
}

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m datapipeline.prepare_country <country>")
        print(f"\nSupported countries ({len(SUPPORTED_COUNTRIES)}):")
        for country in sorted(SUPPORTED_COUNTRIES.keys()):
            print(f"  - {country}")
        sys.exit(1)
    
    country = sys.argv[1].lower().replace('-', '_').replace(' ', '_')
    
    if country not in SUPPORTED_COUNTRIES:
        print(f"Error: Country '{country}' not supported yet.")
        print(f"\nSupported countries ({len(SUPPORTED_COUNTRIES)}):")
        for c in sorted(SUPPORTED_COUNTRIES.keys()):
            print(f"  - {c}")
        print(f"\nTo add support, create: datapipeline/prepare_country/{country}.py")
        sys.exit(1)
    
    # Import and run the country-specific module
    module_name = SUPPORTED_COUNTRIES[country]
    module = importlib.import_module(f'.{module_name}', package='datapipeline.prepare_country')
    
    module.main()

if __name__ == '__main__':
    main()
