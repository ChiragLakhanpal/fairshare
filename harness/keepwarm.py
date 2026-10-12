"""Keeps the Free Edition warehouse awake during a demo (it auto-stops after 10 idle minutes and that is not editable).

  FAIRSHARE_BACKEND=databricks python -m harness.keepwarm     # pings every 4 minutes until Ctrl-C
"""
import time

from fairshare.dbx import warm_warehouse


def main():
    while True:
        try:
            print(time.strftime("%H:%M:%S"), warm_warehouse())
        except Exception as e:
            print(time.strftime("%H:%M:%S"), "warm failed:", e)
        time.sleep(240)


if __name__ == "__main__":
    main()
