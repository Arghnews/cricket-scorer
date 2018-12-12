# This file is executed on every boot (including wake-boot from deepsleep)
import esp
esp.osdebug(9)
import gc
#import webrepl
#webrepl.start()
gc.collect()

