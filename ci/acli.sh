#!/bin/bash
PROJECT="ikeys"
ARDDIR=/tmp/acli_${PROJECT}_$$
if [ ! -d ${ARDDIR} ]
then
    export ARDUINO_BOARD_MANAGER_ADDITIONAL_URLS="https://espressif.github.io/arduino-esp32/package_esp32_index.json"
    export ARDUINO_LIBRARY_ENABLE_UNSAFE_INSTALL=1
    export ARDUINO_DIRECTORIES_DATA="${ARDDIR}/data"
    export ARDUINO_DIRECTORIES_USER="${ARDDIR}/user"
    export LIBDIR="${ARDUINO_DIRECTORIES_USER}/libraries"
    mkdir -p ${LIBDIR}
    # Install board support files
    PLATFORM="esp32:esp32"
    BOARD="${PLATFORM}:esp32s3"
    COREVER=""
    UPLOADPORT="/dev/ttyACM2"
    # list all board options: arduino-cli board details --no-color -b $BOARD
    BOARD_OPTIONS="--board-options USBMode=default,CDCOnBoot=default"
    arduino-cli core --no-color update-index
    arduino-cli core --no-color install ${PLATFORM}${COREVER}
    arduino-cli core --no-color list
    # Install libraries
    arduino-cli lib --no-color update-index
    arduino-cli lib --no-color install "WiFiManager"
    arduino-cli lib --no-color install "M5GFX"
    arduino-cli lib --no-color install "WebSockets"
    arduino-cli lib --no-color list
    # convenience commands
    alias cc="arduino-cli compile -u --port ${UPLOADPORT} ${BOARD_OPTIONS} --fqbn ${BOARD} --output-dir \"./build\" ."
    alias up="arduino-cli upload  --port ${UPLOADPORT} ${BOARD_OPTIONS} --fqbn ${BOARD} --input-dir \"./build\" . && arduino-cli monitor --port ${UPLOADPORT}"
fi
arduino-cli compile --clean -u --port ${UPLOADPORT} ${BOARD_OPTIONS} --fqbn ${BOARD} --output-dir "./build" .
python3 -m pytest test/ -v
