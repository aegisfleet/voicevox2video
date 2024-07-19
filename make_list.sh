#!/bin/bash

set -o errexit
set -o nounset
set -o pipefail

is_binary_file() {
  local file="$1"
  local file_output
  file_output=$(file "$file")
  
  if [[ "$file_output" == *"text"* ]]; then
    return 1
  else
    return 0
  fi
}

initialize_output_file() {
  local folder_name
  folder_name=$(basename "$PWD")
  output_file="${folder_name}.txt"
  : > "$output_file"
}

append_find_output() {
  echo "## Find Output" | tee -a "$output_file"
  find . -type f -not -path '*/.git/*' -exec ls -lh {} \; | tee -a "$output_file"
}

append_source_code() {
  local find_output
  find_output=$(find . -type f -not -path '*/.git/*')

  echo "## Source Code" | tee -a "$output_file"

  while IFS= read -r line; do
    if [[ "$line" != "./$output_file" ]] && ! is_binary_file "$line"; then
      local file_size
      file_size=$(stat -c%s "$line")
      if (( file_size <= 10240 )); then
        {
          echo "\`\`\`file:$line"
          cat "$line"
          echo "\`\`\`"
          echo
        } | tee -a "$output_file"
        echo "Processed: $line"
      else
        echo "Ignored (file too large): $line"
      fi
    else
      if [[ "$line" == "./$output_file" ]]; then
        echo "Ignored (output file): $line"
      else
        echo "Ignored (binary file): $line"
      fi
    fi
  done <<< "$find_output"
}

append_output_file_size() {
  local output_file_size
  output_file_size=$(stat -c%s "$output_file")
  echo "## Output File Size" | tee -a "$output_file"
  echo "Output file size: $output_file_size bytes" | tee -a "$output_file"
}

main() {
  initialize_output_file
  append_find_output
  append_source_code
  append_output_file_size
}

main "$@"
