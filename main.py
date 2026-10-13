# API para a rede de lanchonetes Raízes do Nordeste
# Desenvolvido para gestão de pedidos e integração de canais (App, Totem e Balcão)

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(
    title="Raízes do Nordeste - API de Pedidos",
    description="Backend centralizador de pedidos omnicanal e fidelidade LGPD",
    version="1.0.0"
)

class CanalVenda(str, Enum):
    APP = "APP"
    TOTEM = "TOTEM"
    BALCAO = "BALCAO"
    PICKUP = "PICKUP"

class StatusPedido(str, Enum):
    PENDENTE = "PENDENTE"
    PAGO = "PAGO"
    CANCELADO = "CANCELADO"

class ItemPedido(BaseModel):
    produto_id: str = Field(..., example="CUSCUZ-REC-01")
    nome: str = Field(..., example="Cuscuz Recheado com Queijo Coalho")
    quantidade: int = Field(..., gt=0, example=2)
    preco_unitario: float = Field(..., gt=0.0, example=16.50)

class PedidoDTO(BaseModel):
    unidade_id: str = Field(..., example="REC-CENTRO")
    canal: CanalVenda
    itens: List[ItemPedido]
    cpf_cliente: Optional[str] = Field(None, example="12345678900")
    optin_lgpd: bool = Field(False, description="Consentimento para programa de fidelidade")

class PedidoResponse(BaseModel):
    pedido_id: str
    unidade_id: str
    canal: CanalVenda
    valor_total: float
    pontos_fidelidade: int
    status: StatusPedido
    data_criacao: str

# Simulando persistência temporária no servidor
banco_memoria = {}
estoque_unidades = {
    "REC-CENTRO": {
        "CUSCUZ-REC-01": 30,
        "CAFE-01": 100
    }
}

@app.get("/")
def healthcheck():
    return {"status": "ok", "mensagem": "API Raízes do Nordeste operando normalmente."}

@app.post("/api/v1/pedidos", response_model=PedidoResponse, status_code=status.HTTP_201_CREATED)
def cadastrar_pedido(payload: PedidoDTO):
    if not payload.itens:
        raise HTTPException(status_code=400, detail="Não é possível criar um pedido sem itens.")

    # Checa estoque na unidade informada
    estoque_loja = estoque_unidades.get(payload.unidade_id, {})
    for item in payload.itens:
        disponivel = estoque_loja.get(item.produto_id, 0)
        if disponivel < item.quantidade:
            raise HTTPException(
                status_code=422, 
                detail=f"O produto {item.nome} está sem estoque suficiente na unidade."
            )

    # Cálculo do valor final do pedido
    total = sum(i.quantidade * i.preco_unitario for i in payload.itens)

    # Regra da LGPD: calcula pontos de fidelidade apenas se houver consentimento explícito
    pontos = 0
    if payload.cpf_cliente and payload.optin_lgpd:
        pontos = int(total) # 1 ponto a cada R$ 1,00 em compras

    # Atualiza estoque simulado
    for item in payload.itens:
        estoque_unidades[payload.unidade_id][item.produto_id] -= item.quantidade

    id_gerado = f"PED-{str(uuid.uuid4())[:8].upper()}"
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    registro_pedido = {
        "pedido_id": id_gerado,
        "unidade_id": payload.unidade_id,
        "canal": payload.canal,
        "valor_total": round(total, 2),
        "pontos_fidelidade": pontos,
        "status": StatusPedido.PENDENTE,
        "data_criacao": agora
    }

    banco_memoria[id_gerado] = registro_pedido
    return registro_pedido

@app.post("/api/v1/pedidos/{pedido_id}/confirmar-pagamento", response_model=PedidoResponse)
def webhook_pagamento_confirmado(pedido_id: str):
    pedido = banco_memoria.get(pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido informado não foi encontrado.")

    pedido["status"] = StatusPedido.PAGO
    return pedido