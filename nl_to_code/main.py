#!/usr/bin/env python3
import os
import json
import sys
import requests

from nl_to_code import execute_code_from


def compter(a,b):
    return a+b

tool_mapping = {
    "compter": compter
}

res = execute_code_from(nl="Additionne 56366 et 45", filter_path="main", tools=tool_mapping)
print("Résultat final:", res)