from django.conf import settings

from marketplace.clients.base import RequestClient


class ZeroShotAuthorization:
    BASE_URL = settings.ZEROSHOT_URL
    ACCESS_TOKEN = settings.ZEROSHOT_ACCESS_TOKEN

    def __init__(self):
        self.access_token = self.ACCESS_TOKEN

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}

    @property
    def url(self):
        return self.BASE_URL


class ZeroShotClient(ZeroShotAuthorization, RequestClient):
    def __init__(self):
        super().__init__()
        self.options = [
            {
                "class": "Produtos para adultos",
                "context": (
                    "Proibido promover produtos de prazer ou aprimoramento sexual, incluindo pornografia "
                    "e roupas íntimas usadas. Permitido anunciar lubrificantes e preservativos."
                ),
            },
            {
                "class": "Álcool",
                "context": (
                    "Proibido promover a venda de álcool ou kits de fabricação. Permitido anunciar livros "
                    "e acessórios relacionados."
                ),
            },
            {
                "class": "Partes e fluidos do corpo",
                "context": (
                    "Proibido promover a venda de partes ou fluidos do corpo. Permitido anunciar extensões "
                    "capilares e perucas."
                ),
            },
            {
                "class": "Mídia digital e dispositivos eletrônicos",
                "context": (
                    "Proibido promover dispositivos que facilitam acesso não autorizado a conteúdo digital. "
                    "Permitido anunciar acessórios para dispositivos de streaming."
                ),
            },
            {
                "class": "Discriminação",
                "context": (
                    "Proibido discriminar ou sugerir preferências baseadas em características pessoais "
                    "em anúncios."
                ),
            },
            {
                "class": "Documentos, moedas e instrumentos financeiros",
                "context": (
                    "Proibido promover a venda de documentos, moedas, instrumentos financeiros e criptomoedas. "
                    "Proibido anunciar serviços financeiros."
                ),
            },
            {
                "class": "Jogos de azar",
                "context": (
                    "Proibido promover jogos de azar online por dinheiro ou valor."
                ),
            },
            {
                "class": "Itens e materiais perigosos",
                "context": (
                    "Proibido promover a venda de materiais perigosos, incluindo substâncias corrosivas "
                    "e inflamáveis."
                ),
            },
            {
                "class": "Exploração humana e serviços sexuais",
                "context": (
                    "Proibido promover formas de exploração humana, tráfico, prostituição e pornografia "
                    "infantil."
                ),
            },
            {
                "class": "Suplementos para ingestão",
                "context": (
                    "Proibido promover a venda de suplementos alimentares controlados."
                ),
            },
            {
                "class": "Empregos",
                "context": (
                    "Proibido promover esquemas de 'enriquecimento rápido' e marketing multinível."
                ),
            },
            {
                "class": "Terrenos, animais e produtos de origem animal",
                "context": (
                    "Proibido promover a venda de animais vivos ou abatidos, partes derivadas da carne animal, "
                    "produtos derivados como pele ou carnes, como por exemplo, filé de frango, outro animal "
                    "ou pedaços como picanha, alcatra e outras carnes que provem de partes de quaisquer "
                    "animal. também é proibido a venda de terrenos em áreas de conservação."
                ),
            },
            {
                "class": "Produtos médicos e de saúde",
                "context": (
                    "Proibido promover produtos e serviços médicos não autorizados. Permitido anunciar "
                    "acessórios de fitness e testes de saúde pessoal."
                ),
            },
            {
                "class": "Ofertas e produtos enganosos, violentos ou de incitação ao ódio",
                "context": (
                    "Proibido promover produtos ou conteúdos que sejam enganosos, violentos ou incitem ódio."
                ),
            },
            {
                "class": "Nenhum item para venda",
                "context": (
                    "Proibido promover conteúdo que não esteja associado à venda de um produto."
                ),
            },
            {
                "class": "Produtos com prescrição médica, drogas ou apetrechos para consumo de drogas",
                "context": (
                    "Proibido promover a venda de medicamentos prescritos e apetrechos para drogas."
                ),
            },
            {
                "class": "Produtos recolhidos",
                "context": (
                    "Proibido promover a venda de produtos que foram recolhidos oficialmente."
                ),
            },
            {
                "class": "Serviços",
                "context": (
                    "Proibido anunciar serviços que incluem manutenção de veículos, cuidados pessoais "
                    "e serviços de viagem."
                ),
            },
            {
                "class": "Produtos com apelo sexual",
                "context": (
                    "Proibido promover produtos de maneira sexualmente sugestiva. Restrições específicas "
                    "sobre imagens e atos implícitos."
                ),
            },
            {
                "class": "Itens roubados",
                "context": ("Proibido promover a venda de itens roubados."),
            },
            {
                "class": "Assinaturas e produtos digitais",
                "context": (
                    "Proibido promover a venda de conteúdo digital baixável, contas e assinaturas digitais."
                ),
            },
            {
                "class": "Violação de terceiros",
                "context": (
                    "Proibido anunciar produtos que infrinjam direitos de propriedade intelectual."
                ),
            },
            {
                "class": "Produtos de tabaco e apetrechos relacionados",
                "context": (
                    "Proibido promover a venda de produtos de tabaco e apetrechos relacionados."
                ),
            },
            {
                "class": "Cosméticos usados",
                "context": (
                    "Proibido promover a venda de cosméticos usados ou fora da embalagem original."
                ),
            },
            {
                "class": "Peças e acessórios de veículos",
                "context": (
                    "Proibido promover a venda de peças e acessórios de veículos específicos."
                ),
            },
            {
                "class": "Armas, munições e explosivos",
                "context": (
                    "Proibido promover a venda de armas, munições e explosivos."
                ),
            },
            {
                "class": "Ingressos para eventos ou acesso",
                "context": (
                    "Proibido promover a venda de ingressos para eventos e passagens de transporte."
                ),
            },
            {
                "class": "Vales-presente e vouchers",
                "context": ("Proibido promover a venda de vales-presente e vouchers."),
            },
            {
                "class": "Serviços de correspondência para adoção de animais de estimação",
                "context": (
                    "Restrito a parceiros verificados para promoção de adoção ou venda de animais "
                    "de estimação."
                ),
            },
        ]

    def validate_product_policy(self, product_description):
        url = self.url
        context = (
            "Você é um especialista em categorizar produtos conforme políticas específicas."
            "Avalie a descrição do produto considerando sua natureza, "
            "uso pretendido e características para determinar se ele se enquadra em categorias proibidas ou restritas."
        )
        data = {
            "context": context,
            "language": "por",
            "text": product_description,
            "options": self.options,
        }
        response = self.make_request(
            url, method="POST", headers=self.headers, json=data
        )

        return response.json()
