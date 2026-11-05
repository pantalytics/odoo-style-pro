"""Create the two draft vendor bills the e2e scripts use: id 1 with a PDF, id 2 without.

Run against a fresh database: python3 tools/e2e/setup_bills.py path/to/any.pdf
"""
import base64
import sys
import xmlrpc.client

URL, DB = "http://localhost:8069", "t"
uid = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common").authenticate(DB, "admin", "admin", {})
models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")


def x(*args, **kw):
    return models.execute_kw(DB, uid, "admin", *args, **kw)


partner = x("res.partner", "create", [{"name": "Fieten Olie"}])
bill = x("account.move", "create", [{"move_type": "in_invoice", "partner_id": partner}])
x("account.move", "create", [{"move_type": "in_invoice", "partner_id": partner}])
data = base64.b64encode(open(sys.argv[1], "rb").read()).decode()
att = x("ir.attachment", "create", [{"name": "bill.pdf", "datas": data, "res_model": "account.move", "res_id": bill, "mimetype": "application/pdf"}])
x("account.move", "message_post", [[bill]], {"attachment_ids": [att], "body": "bill"})
print("bills created")
