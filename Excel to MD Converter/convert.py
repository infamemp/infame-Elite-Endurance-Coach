import pandas as pd

# Ask the user for the filename
input_file = input("Enter your Excel filename (e.g., Athlete Template.xlsx): ")
output_file = input_file.replace('.xlsx', '.md')

try:
    # Read the Excel file
    df = pd.read_excel(input_file)

    # Convert to Markdown table
    md_table = df.to_markdown(index=False)

    # Write to .md file
    with open(output_file, 'w') as f:
        f.write(md_table)

    print(f"✓ Success! Created {output_file}")
except FileNotFoundError:
    print(f"❌ Error: {input_file} not found in this folder")
except Exception as e:
    print(f"❌ Error: {e}")