#!/bin/bash

# 1. Unbind the AXI driver to prevent kernel polling
if [ -e /sys/bus/platform/drivers/gpio-xilinx/41200000.gpio ]; then
    echo 41200000.gpio > /sys/bus/platform/drivers/gpio-xilinx/unbind
fi

# 2. Decouple
echo 1 > /sys/class/gpio/gpio598/value

# 3. Load (Ensure -f Partial is used)
fpgautil -b $1 -f Partial

# 4. Thaw
echo 0 > /sys/class/gpio/gpio598/value

# 5. Re-bind the driver so /sys/class/gpio/ reappears
echo 41200000.gpio > /sys/bus/platform/drivers/gpio-xilinx/bind

echo "Partial Reconfiguration Complete: $1"
