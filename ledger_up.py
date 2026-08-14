#!/usr/bin/env python3
"""Manually (re)start the von-network Indy ledger on its own."""

from scripts.ledger import ensure_ledger_up

if __name__ == "__main__":
    ensure_ledger_up()
