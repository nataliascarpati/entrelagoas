#!/usr/bin/env python3
"""Transforma a cópia do WordPress do Entre Lagoas numa vitrine estática.

- remove rastreadores (Facebook, Google, Mailchimp) e scripts suspeitos
- esconde carrinho, conta, busca, lista de desejos e aviso de cookies
- troca o botão de compra por um contato por e-mail
- lista no relatório qualquer código suspeito encontrado

Uso: python3 ferramentas/limpar.py PASTA
"""
import os
import re
import sys

EMAIL = "contato@entrelagoas.com"

RASTREADORES = re.compile(
    r"facebook|fbevents|fbq\(|googletagmanager|gtag\(|google-analytics|dataLayer|"
    r"chimpstatic|mailchimp|mc4wp|hotjar|clarity\.ms|pixel", re.I)
SUSPEITO = re.compile(
    r"eval\(|atob\(|String\.fromCharCode|document\.write\(unescape|\\x[0-9a-f]{2}\\x|"
    r"window\.location\s*=\s*['\"]https?://(?!entrelagoas)", re.I)

CSS_EXTRA = """
<style id="vitrine">
.ast-header-woo-cart,.ast-site-header-cart,.woocommerce-mini-cart,.ast-header-account,
.ast-header-search,.astra-search-shortcode,.ast-search-menu-icon,.jet-ajax-search,.yith-wcwl-add-to-wishlist,.yith-add-to-wishlist-button-block,
#cookie-law-info-bar,.cli-modal,.cli-modal-backdrop,.cky-consent-container,
form.cart,.single_add_to_cart_button,.add_to_cart_button,.ajax_add_to_cart,
.woocommerce-product-details__short-description + .quantity,.mc4wp-form,
a[href*="minha-conta"],a[href*="carrinho"],.woocommerce-store-notice{display:none!important}
.vitrine-contato{display:inline-block;margin:1rem 0;padding:.8em 1.6em;border:1px solid currentColor;
text-decoration:none;letter-spacing:.06em;text-transform:uppercase;font-size:.85rem}
.vitrine-aviso{padding:.6em 1em;text-align:center;font-size:.85rem;background:#f3eee6;color:#5b4a36}
</style>
"""

AVISO = (f'<div class="vitrine-aviso">Loja em pausa. Para encomendas, escreva para '
         f'<a href="mailto:{EMAIL}">{EMAIL}</a>.</div>')


def limpar_scripts(html, relatorio, arquivo):
    def troca(m):
        bloco = m.group(0)
        if RASTREADORES.search(bloco):
            return ""
        if SUSPEITO.search(bloco):
            relatorio.append(f"{arquivo}: script suspeito removido: {bloco[:160]!r}")
            return ""
        return bloco
    html = re.sub(r"<script\b[^>]*>.*?</script>", troca, html, flags=re.S | re.I)
    html = re.sub(r"<noscript>\s*<img[^>]*facebook[^>]*>\s*</noscript>", "", html, flags=re.I)
    # iframes externos estranhos
    for m in re.finditer(r"<iframe[^>]*src=['\"]([^'\"]+)", html, re.I):
        if "youtube" not in m.group(1) and "vimeo" not in m.group(1):
            relatorio.append(f"{arquivo}: iframe externo: {m.group(1)[:120]}")
    return html


def botao_contato(html):
    def troca(m):
        nome = re.search(r'<h1[^>]*product_title[^>]*>(.*?)</h1>', html, re.S)
        assunto = re.sub(r"<[^>]+>|\s+", " ", nome.group(1)).strip() if nome else "Encomenda"
        return (m.group(0) + f'<a class="vitrine-contato" href="mailto:{EMAIL}?subject='
                f'{assunto.replace(" ", "%20")}">Encomendar por e-mail</a>')
    return re.sub(r'<p class="price">.*?</p>', troca, html, count=1, flags=re.S)


def main(pasta):
    relatorio = []
    paginas = 0
    for raiz, _, arquivos in os.walk(pasta):
        for nome in arquivos:
            caminho = os.path.join(raiz, nome)
            if nome.endswith((".js",)) or "@" in nome and ".js" in nome:
                with open(caminho, encoding="utf-8", errors="ignore") as f:
                    js = f.read()
                if SUSPEITO.search(js[:4000]) and "wp-includes" not in caminho and "plugins" not in caminho:
                    relatorio.append(f"{caminho}: arquivo JS com padrão suspeito")
                continue
            if not nome.endswith(".html"):
                continue
            with open(caminho, encoding="utf-8", errors="ignore") as f:
                html = f.read()
            html = limpar_scripts(html, relatorio, caminho)
            html = botao_contato(html)
            html = html.replace("</head>", CSS_EXTRA + "</head>", 1)
            html = re.sub(r"(<body[^>]*>)", r"\1" + AVISO, html, count=1)
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(html)
            paginas += 1
    with open(os.path.join(pasta, "..", "relatorio-limpeza.txt"), "w", encoding="utf-8") as f:
        f.write(f"{paginas} páginas tratadas\n" + "\n".join(relatorio) + "\n")
    print(f"{paginas} páginas tratadas, {len(relatorio)} alertas")
    print("\n".join(relatorio[:50]))


if __name__ == "__main__":
    main(sys.argv[1])
