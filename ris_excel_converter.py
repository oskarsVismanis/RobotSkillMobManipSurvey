import os
import pandas as pd
from pathlib import Path
import re

def excel_to_ris(excel_file, output_ris_file, use_original_year=True):
    """Convert Excel file back to RIS format.
    
    Args:
        excel_file: Path to Excel file created by this script
        output_ris_file: Output RIS file path
        use_original_year: Whether to use Year_Original column if available
    """
    try:
        # Read Excel file
        df = pd.read_excel(excel_file, engine='openpyxl')
        print(f"Reading {len(df)} records from {excel_file}")
        
        with open(output_ris_file, 'w', encoding='utf-8') as f:
            for _, row in df.iterrows():
                # Start of record - determine type
                record_type = row.get('Type', 'JOUR')  # Default to journal article
                f.write(f"TY  - {record_type}\n")
                
                # Title
                if pd.notna(row.get('Title')):
                    f.write(f"TI  - {row['Title']}\n")
                
                # Authors - handle semicolon-separated values
                if pd.notna(row.get('Authors')):
                    authors = str(row['Authors']).split('; ')
                    for author in authors:
                        if author.strip():
                            f.write(f"AU  - {author.strip()}\n")
                
                # Journal
                if pd.notna(row.get('Journal')):
                    f.write(f"JO  - {row['Journal']}\n")
                
                # Year - prefer original if available and requested
                year_value = None
                if use_original_year and pd.notna(row.get('Year_Original')):
                    year_value = row['Year_Original']
                elif pd.notna(row.get('Year')):
                    year_value = row['Year']
                
                if year_value is not None:
                    f.write(f"PY  - {year_value}\n")
                
                # Volume
                if pd.notna(row.get('Volume')):
                    f.write(f"VL  - {row['Volume']}\n")
                
                # Issue
                if pd.notna(row.get('Issue')):
                    f.write(f"IS  - {row['Issue']}\n")
                
                # Pages - handle different formats
                if pd.notna(row.get('Pages')):
                    # If we have a combined Pages field
                    pages = str(row['Pages'])
                    if '-' in pages:
                        start_page, end_page = pages.split('-', 1)
                        f.write(f"SP  - {start_page.strip()}\n")
                        f.write(f"EP  - {end_page.strip()}\n")
                    else:
                        f.write(f"SP  - {pages}\n")
                else:
                    # Handle separate start/end page fields
                    if pd.notna(row.get('Start_Page')):
                        f.write(f"SP  - {row['Start_Page']}\n")
                    if pd.notna(row.get('End_Page')):
                        f.write(f"EP  - {row['End_Page']}\n")
                
                # Abstract
                if pd.notna(row.get('Abstract')):
                    f.write(f"AB  - {row['Abstract']}\n")
                
                # DOI
                if pd.notna(row.get('DOI')):
                    f.write(f"DO  - {row['DOI']}\n")
                elif pd.notna(row.get('DOI_or_Report')):
                    f.write(f"DO  - {row['DOI_or_Report']}\n")
                
                # URL
                if pd.notna(row.get('URL')):
                    f.write(f"UR  - {row['URL']}\n")
                
                # Keywords - handle semicolon-separated values
                if pd.notna(row.get('Keywords')):
                    keywords = str(row['Keywords']).split('; ')
                    for keyword in keywords:
                        if keyword.strip():
                            f.write(f"KW  - {keyword.strip()}\n")
                
                # Publisher (for books)
                if pd.notna(row.get('Publisher')):
                    f.write(f"PB  - {row['Publisher']}\n")
                
                # Book Title (for book chapters)
                if pd.notna(row.get('Book_Title')):
                    f.write(f"BT  - {row['Book_Title']}\n")
                
                # Series
                if pd.notna(row.get('Series')):
                    f.write(f"T3  - {row['Series']}\n")
                
                # City
                if pd.notna(row.get('City')):
                    f.write(f"CY  - {row['City']}\n")
                
                # Editors - handle semicolon-separated values
                if pd.notna(row.get('Editors')):
                    editors = str(row['Editors']).split('; ')
                    for editor in editors:
                        if editor.strip():
                            f.write(f"ED  - {editor.strip()}\n")
                
                # Add any custom ENW fields that were preserved
                for col in df.columns:
                    if col.startswith('ENW_') and pd.notna(row.get(col)):
                        # Convert back to RIS equivalent or custom tag
                        f.write(f"N1  - {col}: {row[col]}\n")  # Store as note
                
                # End of record
                f.write("ER  - \n\n")
        
        print(f"Successfully converted {len(df)} records to RIS format: {output_ris_file}")
        
    except Exception as e:
        print(f"Error converting Excel to RIS: {e}")

def excel_to_ris_with_filters(excel_file, output_ris_file, year_range=None, 
                             keywords_filter=None, authors_filter=None):
    """Convert Excel file to RIS with optional filtering.
    
    Args:
        excel_file: Path to Excel file
        output_ris_file: Output RIS file path
        year_range: Tuple (min_year, max_year) to filter by year
        keywords_filter: List of keywords to filter by (OR logic)
        authors_filter: List of author names to filter by (OR logic)
    """
    try:
        # Read Excel file
        df = pd.read_excel(excel_file, engine='openpyxl')
        original_count = len(df)
        print(f"Reading {original_count} records from {excel_file}")
        
        # Apply filters
        if year_range:
            min_year, max_year = year_range
            year_col = 'Year' if 'Year' in df.columns else 'Year_Original'
            if year_col in df.columns:
                df = df[(df[year_col] >= min_year) & (df[year_col] <= max_year)]
                print(f"Filtered by year ({min_year}-{max_year}): {len(df)} records remaining")
        
        if keywords_filter and 'Keywords' in df.columns:
            keyword_mask = df['Keywords'].fillna('').str.contains('|'.join(keywords_filter), case=False, na=False)
            df = df[keyword_mask]
            print(f"Filtered by keywords {keywords_filter}: {len(df)} records remaining")
        
        if authors_filter and 'Authors' in df.columns:
            author_mask = df['Authors'].fillna('').str.contains('|'.join(authors_filter), case=False, na=False)
            df = df[author_mask]
            print(f"Filtered by authors {authors_filter}: {len(df)} records remaining")
        
        if len(df) == 0:
            print("No records match the specified filters")
            return
        
        # Convert filtered data to RIS
        with open(output_ris_file, 'w', encoding='utf-8') as f:
            for _, row in df.iterrows():
                # Start of record
                record_type = row.get('Type', 'JOUR')
                f.write(f"TY  - {record_type}\n")
                
                # Title
                if pd.notna(row.get('Title')):
                    f.write(f"TI  - {row['Title']}\n")
                
                # Authors
                if pd.notna(row.get('Authors')):
                    authors = str(row['Authors']).split('; ')
                    for author in authors:
                        if author.strip():
                            f.write(f"AU  - {author.strip()}\n")
                
                # Journal
                if pd.notna(row.get('Journal')):
                    f.write(f"JO  - {row['Journal']}\n")
                
                # Year
                year_value = row.get('Year_Original') if pd.notna(row.get('Year_Original')) else row.get('Year')
                if pd.notna(year_value):
                    f.write(f"PY  - {year_value}\n")
                
                # Volume
                if pd.notna(row.get('Volume')):
                    f.write(f"VL  - {row['Volume']}\n")
                
                # Issue
                if pd.notna(row.get('Issue')):
                    f.write(f"IS  - {row['Issue']}\n")
                
                # Pages
                if pd.notna(row.get('Pages')):
                    pages = str(row['Pages'])
                    if '-' in pages:
                        start_page, end_page = pages.split('-', 1)
                        f.write(f"SP  - {start_page.strip()}\n")
                        f.write(f"EP  - {end_page.strip()}\n")
                    else:
                        f.write(f"SP  - {pages}\n")
                else:
                    if pd.notna(row.get('Start_Page')):
                        f.write(f"SP  - {row['Start_Page']}\n")
                    if pd.notna(row.get('End_Page')):
                        f.write(f"EP  - {row['End_Page']}\n")
                
                # Abstract
                if pd.notna(row.get('Abstract')):
                    f.write(f"AB  - {row['Abstract']}\n")
                
                # DOI
                if pd.notna(row.get('DOI')):
                    f.write(f"DO  - {row['DOI']}\n")
                
                # URL
                if pd.notna(row.get('URL')):
                    f.write(f"UR  - {row['URL']}\n")
                
                # Keywords
                if pd.notna(row.get('Keywords')):
                    keywords = str(row['Keywords']).split('; ')
                    for keyword in keywords:
                        if keyword.strip():
                            f.write(f"KW  - {keyword.strip()}\n")
                
                # End of record
                f.write("ER  - \n\n")
        
        print(f"Successfully converted {len(df)} filtered records to RIS format: {output_ris_file}")
        print(f"Filtered out {original_count - len(df)} records")
        
    except Exception as e:
        print(f"Error converting Excel to RIS with filters: {e}")

def normalize_year(year_value):
    """Extract and normalize year from various formats.
    
    Handles formats like:
    - '2023'
    - '2023/01/15'
    - '2023-05-20'
    - 'c2023'
    - '2023//'
    - '2023-2024' (takes first year)
    
    Returns:
        int: Normalized year as integer, or None if no valid year found
    """
    if not year_value:
        return None
    
    # Convert to string and clean
    year_str = str(year_value).strip()
    
    # Remove common prefixes
    year_str = re.sub(r'^[cp]\.?\s*', '', year_str, flags=re.IGNORECASE)
    
    # Extract 4-digit year patterns
    year_patterns = [
        r'(\d{4})',  # Basic 4-digit year
        r'(\d{4})[/-]',  # Year followed by separator
        r'^(\d{4})',  # Year at start
    ]
    
    for pattern in year_patterns:
        match = re.search(pattern, year_str)
        if match:
            year = int(match.group(1))
            # Validate reasonable year range
            if 1800 <= year <= 2030:
                return year
    
    return None

def normalize_title(title):
    """Normalize title for comparison by removing punctuation and extra spaces."""
    if not title:
        return ""
    
    # Convert to lowercase and remove common punctuation
    normalized = re.sub(r'[^\w\s]', '', title.lower())
    # Remove extra whitespace
    normalized = ' '.join(normalized.split())
    return normalized

def calculate_similarity(title1, title2):
    """Calculate simple similarity between two titles based on word overlap."""
    if not title1 or not title2:
        return 0.0
    
    words1 = set(title1.lower().split())
    words2 = set(title2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) if union else 0.0

def remove_duplicate_titles(records, strategy='exact'):
    """Remove duplicate records based on title similarity.
    
    Args:
        records: List of record dictionaries
        strategy: 'exact', 'fuzzy', or 'normalized'
    
    Returns:
        List of deduplicated records
    """
    if not records:
        return records
    
    seen_titles = set()
    unique_records = []
    duplicates_found = 0
    
    print(f"Removing duplicates using '{strategy}' strategy...")
    
    for record in records:
        title = record.get('Title', '')
        
        if not title:  # Keep records without titles
            unique_records.append(record)
            continue
        
        is_duplicate = False
        
        if strategy == 'exact':
            # Case-insensitive exact match
            title_key = title.lower().strip()
            if title_key in seen_titles:
                is_duplicate = True
            else:
                seen_titles.add(title_key)
        
        elif strategy == 'normalized':
            # Normalized comparison (remove punctuation, extra spaces)
            title_key = normalize_title(title)
            if title_key in seen_titles:
                is_duplicate = True
            else:
                seen_titles.add(title_key)
        
        elif strategy == 'fuzzy':
            # Check similarity with existing titles
            for existing_title in seen_titles:
                similarity = calculate_similarity(title, existing_title)
                if similarity > 0.85:  # 85% similarity threshold
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen_titles.add(title.lower().strip())
        
        if not is_duplicate:
            unique_records.append(record)
        else:
            duplicates_found += 1
            print(f"  Duplicate found: '{title[:60]}{'...' if len(title) > 60 else ''}'")
    
    print(f"Removed {duplicates_found} duplicate(s)")
    return unique_records

def parse_enw_file(file_path):
    """Parse a single ENW (EndNote) file and return a dictionary of records."""
    records = []
    current_record = {}
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            
            # ENW format: %TAG VALUE
            if line.startswith('%'):
                if len(line) < 3:
                    continue
                    
                tag = line[1]  # Single character after %
                value = line[3:].strip() if len(line) > 2 else ""
                
                # Handle different ENW tags
                if tag == '0':  # Type of reference
                    if current_record:  # Save previous record if exists
                        records.append(current_record)
                    current_record = {'Type': value}
                elif tag == 'T':  # Title
                    current_record['Title'] = value
                elif tag == 'A':  # Author
                    if 'Authors' not in current_record:
                        current_record['Authors'] = []
                    current_record['Authors'].append(value)
                elif tag == 'J':  # Journal/Periodical
                    current_record['Journal'] = value
                elif tag == 'B':  # Book title (for book chapters)
                    current_record['Book_Title'] = value
                elif tag == 'D':  # Date/Year
                    current_record['Year'] = value
                elif tag == 'V':  # Volume
                    current_record['Volume'] = value
                elif tag == 'N':  # Number/Issue
                    current_record['Issue'] = value
                elif tag == 'P':  # Pages
                    current_record['Pages'] = value
                elif tag == 'X':  # Abstract
                    current_record['Abstract'] = value
                elif tag == 'U':  # URL
                    current_record['URL'] = value
                elif tag == 'K':  # Keywords
                    if 'Keywords' not in current_record:
                        current_record['Keywords'] = []
                    current_record['Keywords'].append(value)
                elif tag == 'I':  # Publisher
                    current_record['Publisher'] = value
                elif tag == 'C':  # City
                    current_record['City'] = value
                elif tag == 'E':  # Editor
                    if 'Editors' not in current_record:
                        current_record['Editors'] = []
                    current_record['Editors'].append(value)
                elif tag == 'S':  # Series
                    current_record['Series'] = value
                elif tag == 'R':  # DOI or Report Number
                    current_record['DOI_or_Report'] = value
                elif tag == '8':  # Date (alternative)
                    if 'Year' not in current_record:
                        current_record['Year'] = value
                else:
                    # Store other tags as-is
                    current_record[f'ENW_{tag}'] = value
    
    # Add the last record
    if current_record:
        records.append(current_record)
    
    return records

def parse_ris_file(file_path):
    """Parse a single RIS file and return a dictionary of records."""
    records = []
    current_record = {}
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
                
            # Check if this is a tag line (format: TAG  - Value)
            if re.match(r'^[A-Z][A-Z0-9]\s\s-\s', line):
                tag = line[:2]
                value = line[6:].strip()  # Skip "TAG  - " part
                
                # Handle different RIS tags
                if tag == 'TY':  # Type of reference (start of new record)
                    if current_record:  # Save previous record if exists
                        records.append(current_record)
                    current_record = {'Type': value}
                elif tag == 'TI':  # Title
                    current_record['Title'] = value
                elif tag == 'AU':  # Author
                    if 'Authors' not in current_record:
                        current_record['Authors'] = []
                    current_record['Authors'].append(value)
                elif tag == 'JO' or tag == 'JF':  # Journal
                    current_record['Journal'] = value
                elif tag == 'PY' or tag == 'Y1':  # Publication Year
                    current_record['Year'] = value
                elif tag == 'VL':  # Volume
                    current_record['Volume'] = value
                elif tag == 'IS':  # Issue
                    current_record['Issue'] = value
                elif tag == 'SP':  # Start Page
                    current_record['Start_Page'] = value
                elif tag == 'EP':  # End Page
                    current_record['End_Page'] = value
                elif tag == 'AB':  # Abstract
                    current_record['Abstract'] = value
                elif tag == 'DO':  # DOI
                    current_record['DOI'] = value
                elif tag == 'UR':  # URL
                    current_record['URL'] = value
                elif tag == 'KW':  # Keywords
                    if 'Keywords' not in current_record:
                        current_record['Keywords'] = []
                    current_record['Keywords'].append(value)
                elif tag == 'ER':  # End of record
                    if current_record:
                        records.append(current_record)
                        current_record = {}
                else:
                    # Store other tags as-is
                    current_record[tag] = value
    
    # Add the last record if file doesn't end with ER
    if current_record:
        records.append(current_record)
    
    return records

def process_files_to_excel(input_directory, output_file, remove_duplicates=True, duplicate_strategy='exact'):
    """Process all RIS and ENW files in a directory and save to Excel.
    
    Args:
        input_directory: Path to directory containing RIS/ENW files
        output_file: Output Excel file path
        remove_duplicates: Whether to remove duplicate entries (default: True)
        duplicate_strategy: How to identify duplicates:
            - 'exact': Exact title match (case-insensitive)
            - 'fuzzy': Similar titles using text similarity
            - 'normalized': Remove punctuation and extra spaces
    """
    all_records = []
    
    # Find all .ris and .enw files in the directory
    ris_files = list(Path(input_directory).glob('*.ris'))
    enw_files = list(Path(input_directory).glob('*.enw'))
    all_files = ris_files + enw_files
    
    if not all_files:
        print(f"No .ris or .enw files found in {input_directory}")
        return
    
    print(f"Found {len(ris_files)} RIS files and {len(enw_files)} ENW files")
    
    # Process each file
    for file_path in all_files:
        print(f"Processing: {file_path.name}")
        try:
            if file_path.suffix.lower() == '.ris':
                records = parse_ris_file(file_path)
            elif file_path.suffix.lower() == '.enw':
                records = parse_enw_file(file_path)
            else:
                continue
                
            # Add source file information and file type
            for record in records:
                record['Source_File'] = file_path.name
                record['File_Format'] = file_path.suffix.upper()[1:]  # RIS or ENW
            all_records.extend(records)
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")
    
    if not all_records:
        print("No records found in any files")
        return
    
    # Remove duplicates if requested
    if remove_duplicates and all_records:
        all_records = remove_duplicate_titles(all_records, duplicate_strategy)
        print(f"After deduplication: {len(all_records)} records")
    
    # Convert to DataFrame
    # Handle list fields (Authors, Keywords, Editors) by joining with semicolons
    processed_records = []
    for record in all_records:
        processed_record = record.copy()
        
        # Join list fields
        list_fields = ['Authors', 'Keywords', 'Editors']
        for field in list_fields:
            if field in processed_record and isinstance(processed_record[field], list):
                processed_record[field] = '; '.join(processed_record[field])
        
        # Normalize year for sorting
        if 'Year' in processed_record:
            original_year = processed_record['Year']
            normalized_year = normalize_year(original_year)
            processed_record['Year_Normalized'] = normalized_year
            processed_record['Year_Original'] = original_year
            # Keep the normalized year in the main Year column for sorting
            processed_record['Year'] = normalized_year
        
        processed_records.append(processed_record)
    
    df = pd.DataFrame(processed_records)
    
    # Reorder columns for better readability
    preferred_order = ['Source_File', 'File_Format', 'Type', 'Title', 'Authors', 'Editors',
                      'Journal', 'Book_Title', 'Year', 'Year_Original', 'Volume', 'Issue', 
                      'Pages', 'Start_Page', 'End_Page', 'Publisher', 'City', 'Series',
                      'DOI', 'DOI_or_Report', 'URL', 'Abstract', 'Keywords']
    
    # Only include columns that exist in the data
    columns = [col for col in preferred_order if col in df.columns]
    remaining_columns = [col for col in df.columns if col not in columns]
    final_columns = columns + remaining_columns
    
    df = df[final_columns]
    
    # Sort by year (most recent first), then by title
    if 'Year' in df.columns:
        df = df.sort_values(['Year', 'Title'], ascending=[False, True], na_position='last')
        print(f"Data sorted by year (newest first), then by title")
    
    # Save to Excel
    df.to_excel(output_file, index=False, engine='openpyxl')
    print(f"Successfully saved {len(df)} records to {output_file}")
    
    # Print summary with year and format statistics
    print(f"\nSummary:")
    print(f"Total records: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print(f"Files processed: {len(all_files)} ({len(ris_files)} RIS, {len(enw_files)} ENW)")
    
    # File format distribution
    if 'File_Format' in df.columns:
        format_counts = df['File_Format'].value_counts()
        print(f"\nRecords by format:")
        for fmt, count in format_counts.items():
            print(f"  {fmt}: {count} records")
    
    if 'Year' in df.columns:
        year_stats = df['Year'].dropna()
        if not year_stats.empty:
            print(f"\nYear statistics:")
            print(f"  Year range: {int(year_stats.min())} - {int(year_stats.max())}")
            print(f"  Records with valid years: {len(year_stats)}")
            print(f"  Records missing years: {len(df) - len(year_stats)}")
            
            # Show year distribution
            year_counts = df['Year'].value_counts().sort_index(ascending=False).head(80)
            print(f"  Most common years:")
            for year, count in year_counts.items():
                if pd.notna(year):
                    print(f"    {int(year)}: {count} records")

# Example usage
if __name__ == "__main__":
    
    main_dir = "/home/oskars/Research/RobotSkillMobManipSurvey/"
    # behaviour , action , capability , manipulate , motion-movement , motor , navigate , skill , task
    desc_type = "task"

    prefix = main_dir+desc_type

    # Set your input directory containing .ris and .enw files
    input_dir = prefix+"/databases"
    
    # Set output Excel file path
    output_excel = prefix+"/"+desc_type+"_combined_data.xlsx"
    
    # STEP 1: Convert RIS/ENW files to Excel
    print("=== Converting RIS/ENW to Excel ===")
    process_files_to_excel(input_dir, output_excel, 
                          remove_duplicates=True, 
                          duplicate_strategy='exact')
    
    # STEP 2: Convert Excel back to RIS (optional)
    print("\n=== Converting Excel back to RIS ===")
    
    # Option A: Convert entire Excel file back to RIS
    output_ris = prefix+"/"+desc_type+"_combined_bibliography.ris"
    excel_to_ris(output_excel, output_ris, use_original_year=True)
    
    # Option B: Convert with filters (examples)
    # Recent papers only (2020-2024)
    # excel_to_ris_with_filters(output_excel, "recent_papers.ris", 
    #                          year_range=(2020, 2024))
    
    # Papers with specific keywords
    # excel_to_ris_with_filters(output_excel, "ml_papers.ris",
    #                          keywords_filter=['machine learning', 'AI', 'neural'])
    
    # Papers by specific authors
    # excel_to_ris_with_filters(output_excel, "smith_papers.ris",
    #                          authors_filter=['Smith', 'Johnson'])
    
    # Combined filters
    # excel_to_ris_with_filters(output_excel, "recent_ml_papers.ris",
    #                          year_range=(2020, 2024),
    #                          keywords_filter=['machine learning', 'deep learning'])
    
    print("\n=== Processing Complete ===")
    print("Files created:")
    print(f"  Excel: {output_excel}")
    print(f"  RIS: {output_ris}")
    print("You can now import the RIS file into your reference manager!")