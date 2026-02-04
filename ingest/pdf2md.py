#!/bin/env python3
from docling.document_converter import DocumentConverter
import os

converter = DocumentConverter()
source_dir = 'raw-kb'
output_dir = 'text-kb'

for filename in os.listdir(source_dir):
    source_path = os.path.join(source_dir, filename)
    if os.path.isfile(source_path):
        result = converter.convert(source_path)

        base_name, _ = os.path.splitext(filename)  # split the filename and its extension
        output_filename = base_name + '.md'
        output_path = os.path.join(output_dir, output_filename)

        with open(output_path, 'w') as output_file:
            output_file.write(result.document.export_to_markdown())
