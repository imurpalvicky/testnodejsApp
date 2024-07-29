previous_commit=$(git rev-parse HEAD^)
previous_value=$(git show $previous_commit:file.properties | grep "^x=" | cut -d'=' -f2)
current_value=$(grep "^x=" file.properties | cut -d'=' -f2)

if [ "$previous_value" != "$current_value" ]; then
  echo "Attribute x has changed from $previous_value to $current_value"
else
  echo "Attribute x has not changed"
fi