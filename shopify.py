# -*- coding: utf-8 -*-
"""
Resumen mensual por PRODUCTO con paginación de line items:
- venta_bruta = sum(discountedUnitPriceSet * quantity)
- venta_neta  = sum(discountedUnitPriceAfterAllDiscountsSet * quantity)
- impuestos   = sum(taxLines.priceSet)
- neta_sin_impuestos = venta_neta - impuestos
- bruta_sin_impuestos = venta_bruta - impuestos
- descuentos  = venta_bruta - venta_neta
Genera DataFrame por_producto (con stock_total) y podés guardarlo donde quieras.
"""

import os, json, requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pandas as pd

API_VERSION = "2025-07"
SHOP_TZ = os.getenv("SHOP_TZ", "America/Argentina/Buenos_Aires")

def month_bounds_local_to_utc():
    now_local = datetime.now(ZoneInfo(SHOP_TZ))
    start_local = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start_local.astimezone(timezone.utc).isoformat(), now_local.astimezone(timezone.utc).isoformat()

def last_90_days_bounds_local_to_utc():
    now_local = datetime.now(ZoneInfo(SHOP_TZ))
    since_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=90)
    since_iso = since_local.astimezone(timezone.utc).isoformat()
    until_iso = now_local.astimezone(timezone.utc).isoformat()
    return since_iso, until_iso

def construct_search_q(since_iso, until_iso):
    return f"created_at:>={since_iso} created_at:<{until_iso} cancelled_at:null test:false"

# --- Ventas: órdenes + line items ---
ORDERS_GQL = """
query($cursor: String, $q: String!) {
  orders(first: 100, after: $cursor, query: $q, sortKey: CREATED_AT) {
    pageInfo { hasNextPage }
    edges {
      cursor
      node {
        id
        currencyCode
        lineItems(first: 250) {
          pageInfo { hasNextPage }
          edges {
            cursor
            node {
              quantity
              discountedUnitPriceSet { shopMoney { amount } }
              discountedUnitPriceAfterAllDiscountsSet { shopMoney { amount } }
              taxLines { priceSet { shopMoney { amount } } }
              product { id title }
            }
          }
        }
      }
    }
  }
}
"""

LINEITEMS_GQL = """
query($orderId: ID!, $cursor: String) {
  order(id: $orderId) {
    lineItems(first: 250, after: $cursor) {
      pageInfo { hasNextPage }
      edges {
        cursor
        node {
          quantity
          discountedUnitPriceSet { shopMoney { amount } }
          discountedUnitPriceAfterAllDiscountsSet { shopMoney { amount } }
          taxLines { priceSet { shopMoney { amount } } }
          product { id title }
        }
      }
    }
  }
}
"""

# --- Stock por producto (sumando variants.inventoryQuantity) ---
PRODUCTS_STOCK_GQL = """
query($cursor: String) {
  products(first: 100, after: $cursor, sortKey: TITLE) {
    pageInfo { hasNextPage }
    edges {
      cursor
      node {
        id
        title
        variants(first: 250) {
          edges {
            node {
              id
              title
              sku
              inventoryQuantity
            }
          }
        }
      }
    }
  }
}
"""

def gql_post(body: dict, shop_domain, admin_token):
    url = f"https://{shop_domain}/admin/api/{API_VERSION}/graphql.json"
    r = requests.post(
        url,
        headers={"X-Shopify-Access-Token": admin_token, "Content-Type": "application/json"},
        data=json.dumps(body),
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("errors"):
        print("WARN: GraphQL devolvió errores:", data["errors"])
    return data

def fetch_lineitems_all(order_id: str, first_page: dict, shop_domain, admin_token):
    if not first_page:
        return []
    edges = list(first_page.get("edges") or [])
    has_next = (first_page.get("pageInfo") or {}).get("hasNextPage")
    cursor = edges[-1]["cursor"] if edges else None
    while has_next:
        data = gql_post({"query": LINEITEMS_GQL, "variables": {"orderId": order_id, "cursor": cursor}}, shop_domain, admin_token)
        page = (data.get("data") or {}).get("order", {}).get("lineItems", {})
        new_edges = page.get("edges") or []
        if not new_edges:
            break
        edges.extend(new_edges)
        cursor = new_edges[-1]["cursor"]
        has_next = (page.get("pageInfo") or {}).get("hasNextPage")
    return edges

def fetch_stock_actual_por_producto(shop_domain: str, admin_token: str) -> pd.DataFrame:
    cursor = None
    rows = []
    while True:
        data = gql_post({"query": PRODUCTS_STOCK_GQL, "variables": {"cursor": cursor}}, shop_domain, admin_token)
        products = (data.get("data") or {}).get("products", {})
        for edge in products.get("edges", []):
            p = edge["node"]
            pid = p.get("id")
            ptitle = (p.get("title") or "").strip()
            for ve in (p.get("variants") or {}).get("edges", []):
                v = ve["node"]
                inv = v.get("inventoryQuantity")
                try:
                    inv = int(inv) if inv is not None else 0
                except Exception:
                    inv = 0
                rows.append({
                    "product_id": pid,
                    "product_title": ptitle,
                    "variant_id": v.get("id"),
                    "variant_title": (v.get("title") or "").strip(),
                    "sku": v.get("sku") or "",
                    "inventory_quantity": inv,
                })
            cursor = edge["cursor"]
        if not (products.get("pageInfo") or {}).get("hasNextPage"):
            break

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["product_id", "product_title", "stock_total"])

    stock_por_producto = (
        df.groupby(["product_id", "product_title"], dropna=False)
          .agg(stock_total=("inventory_quantity", "sum"))
          .reset_index()
    )
    return stock_por_producto

def f2(x):
    try:
        return float(x)
    except Exception:
        return 0.0

def scrap_shopify(shop_domain, admin_token, last_90_days=False):
    items = []
    cursor = None

    if last_90_days:
        since_iso, until_iso = last_90_days_bounds_local_to_utc()
    else:
        since_iso, until_iso = month_bounds_local_to_utc()
      
    while True:
        data = gql_post({"query": ORDERS_GQL, "variables": {"cursor": cursor, "q": construct_search_q(since_iso, until_iso)}}, shop_domain, admin_token)
        orders = (data.get("data") or {}).get("orders", {})

        for edge in orders.get("edges", []):
            o = edge["node"]
            currency = o.get("currencyCode") or ""

            li_edges = fetch_lineitems_all(o["id"], o.get("lineItems") or {}, shop_domain, admin_token)

            for le in li_edges:
                li = le["node"]

                qty = int(li.get("quantity") or 0)
                prod = li.get("product") or {}
                product_id = prod.get("id") or ""
                product_title = (prod.get("title") or "(Sin título)").strip()

                unit_bruta = f2(((li.get("discountedUnitPriceSet") or {}).get("shopMoney") or {}).get("amount"))
                unit_neta  = f2(((li.get("discountedUnitPriceAfterAllDiscountsSet") or {}).get("shopMoney") or {}).get("amount"))

                line_bruta = unit_bruta * qty
                line_neta  = unit_neta  * qty

                # impuestos del ítem (suma de taxLines)
                tax_sum = 0.0
                for t in (li.get("taxLines") or []):
                    tax_sum += f2(((t.get("priceSet") or {}).get("shopMoney") or {}).get("amount"))
                if tax_sum < 0:
                    tax_sum = 0.0
                if tax_sum > line_neta:
                    tax_sum = line_neta  # no superar la neta

                # descuentos = bruta - neta
                line_desc = line_bruta - line_neta
                if line_desc < 0:
                    line_desc = 0.0
                if line_desc > line_bruta:
                    line_desc = line_bruta

                # netas/brutas sin impuestos
                line_neta_sin_tax  = max(line_neta  - tax_sum, 0.0)
                line_bruta_sin_tax = max(line_bruta - tax_sum, 0.0)

                items.append({
                    "product_id": product_id,
                    "product_title": product_title,
                    "currency": currency,
                    "quantity": qty,
                    "unit_bruta": unit_bruta,
                    "unit_neta": unit_neta,
                    "line_bruta": line_bruta,
                    "line_descuento": line_desc,
                    "line_impuestos": tax_sum,
                    "line_neta": line_neta,
                    "line_neta_sin_impuestos": line_neta_sin_tax,
                    "line_bruta_sin_impuestos": line_bruta_sin_tax,
                })

            cursor = edge["cursor"]

        if not (orders.get("pageInfo") or {}).get("hasNextPage"):
            break

    if not items:
        print("No se encontraron ventas en el período.")
        return pd.DataFrame()

    df = pd.DataFrame(items)

    # Filtro de moneda: ARS
    df = df[df["currency"] == "ARS"].copy()

    # Totales por producto (ventas)
    por_producto = (
        df.groupby(["product_id", "product_title", "currency"], dropna=False)
          .agg(unidades=("quantity", "sum"),
               venta_bruta=("line_bruta", "sum"),
               descuentos=("line_descuento", "sum"),
               impuestos=("line_impuestos", "sum"),
               venta_neta=("line_neta", "sum"),
               neta_sin_impuestos=("line_neta_sin_impuestos", "sum"),
               bruta_sin_impuestos=("line_bruta_sin_impuestos", "sum"))
          .reset_index()
          .sort_values(["unidades", "neta_sin_impuestos"], ascending=[False, False])
    )

    # --- Merge con STOCK por producto (base = stock) ---
    stock_df = fetch_stock_actual_por_producto(shop_domain, admin_token)  # product_id, product_title, stock_total

    # Empezamos desde stock y anexamos métricas de ventas por product_id
    por_producto = stock_df.merge(
        por_producto.drop(columns=["product_title"], errors="ignore"),  # evitamos duplicar título
        on="product_id",
        how="outer"
    )

    # Completar faltantes para productos sin ventas
    num_cols = [
        "unidades","venta_bruta","descuentos","impuestos",
        "venta_neta","neta_sin_impuestos","bruta_sin_impuestos"
    ]
    for c in num_cols:
        por_producto[c] = por_producto[c].fillna(0)

    # Moneda por defecto si no hay ventas
    if "currency" not in por_producto.columns:
        por_producto["currency"] = "ARS"
    else:
        por_producto["currency"] = por_producto["currency"].fillna("ARS")

    por_producto["stock_total"] = por_producto["stock_total"].fillna(0).astype(int)

    return por_producto

