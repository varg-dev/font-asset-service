# test if pip-tools is installed
if ! pip-compile --version; then
  echo "pip-tools is not installed! Please install it via pip install pip-tools"
  exit 2
fi

# cd to the correct directory
FILE=docker-compose.yml
if ! test -f "$FILE"; then
  cd ..
fi

echo "+++++++++++++++++"
echo "updating service"
echo "+++++++++++++++++"
cd service || exit 1
pip-compile requirements.in
cd .. || exit 1
