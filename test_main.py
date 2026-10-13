from fastapi.testclient import TestClient
from main import app, StatusPedido

client = TestClient(app)

def test_fluxo_completo_pedido_e_pagamento():
    """Valida o caminho feliz: criação do pedido e confirmação de pagamento."""
    body = {
        "unidade_id": "REC-CENTRO",
        "canal": "APP",
        "itens": [
            {
                "produto_id": "CUSCUZ-REC-01",
                "nome": "Cuscuz Recheado com Queijo Coalho",
                "quantidade": 2,
                "preco_unitario": 16.50
            }
        ],
        "cpf_cliente": "12345678900",
        "optin_lgpd": True
    }

    # 1. Criação do Pedido
    res = client.post("/api/v1/pedidos", json=body)
    assert res.status_code == 201
    dados = res.json()
    
    assert dados["valor_total"] == 33.00
    assert dados["pontos_fidelidade"] == 33
    assert dados["status"] == StatusPedido.PENDENTE
    
    p_id = dados["pedido_id"]

    # 2. Callback de confirmação do Gateway de Pagamento
    res_pay = client.post(f"/api/v1/pedidos/{p_id}/confirmar-pagamento")
    assert res_pay.status_code == 200
    assert res_pay.json()["status"] == StatusPedido.PAGO

def test_pedido_recusado_por_falta_de_estoque():
    """Valida o comportamento negativo quando a loja não possui o item disponível."""
    body = {
        "unidade_id": "REC-CENTRO",
        "canal": "TOTEM",
        "itens": [
            {
                "produto_id": "CUSCUZ-REC-01",
                "nome": "Cuscuz Recheado com Queijo Coalho",
                "quantidade": 999, # Quantidade acima do estoque inicial (30)
                "preco_unitario": 16.50
            }
        ],
        "optin_lgpd": False
    }

    res = client.post("/api/v1/pedidos", json=body)
    assert res.status_code == 422