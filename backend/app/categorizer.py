import re
from .models import CategoryEnum

CATEGORY_RULES: list[tuple[CategoryEnum, list[str]]] = [
    (CategoryEnum.MERCADO, [
        r"mercado", r"supermercado", r"carrefour", r"extra\b", r"atacad[aã]o",
        r"pao de acucar", r"p[ãa]o de a[cç][uú]car", r"assai", r"assaí",
        r"hortifruti", r"nacional\b", r"coop\b", r"cooperativa", r"makro",
        r"sams club", r"sam'?s\b", r"walmart", r"big\b.*superm",
        r"tenda\b", r"dia\b", r"minuto pao", r"prezunic",
    ]),
    (CategoryEnum.ALIMENTACAO, [
        r"restaurante", r"lanchonete", r"hamburger", r"hamburguer", r"mc donalds",
        r"mcdonald", r"burger king", r"kfc\b", r"subway\b", r"pizza", r"sushi",
        r"ifood", r"i food", r"rappi\b", r"uber eats", r"james delivery",
        r"padaria", r"confeitaria", r"cafeteria", r"caf[eé]\b", r"coffee",
        r"acai", r"a[cç]a[ií]", r"sorvete", r"gelato", r"bar\b",
        r"boteco", r"churrascaria", r"rodizio", r"rod[ií]zio",
        r"bistro", r"bistr[ôo]", r"cantina", r"buffet", r"comida",
        r"delivery", r"lanche\b", r"sanduiche", r"hot dog", r"tapioca",
    ]),
    (CategoryEnum.TRANSPORTE, [
        r"uber\b", r"99\b", r"99taxi", r"taxi\b", r"t[áa]xi",
        r"cabify", r"lyft\b", r"bla bla", r"blablacar",
        r"posto\b", r"combustivel", r"combust[ií]vel", r"gasolina",
        r"etanol", r"alcool\b", r"shell\b", r"petrob", r"br distribuidora",
        r"ipiranga", r"ale combustivel", r"ticket log", r"sem parar",
        r"veloe\b", r"connect car", r"movida", r"localiza", r"unidas\b",
        r"metro\b", r"metrô\b", r"bilhete unico", r"onibus\b",
        r"azul\b.*linhas", r"gol\b.*linhas", r"latam\b", r"tap\b",
        r"porto seguro.*auto",
    ]),
    (CategoryEnum.SAUDE, [
        r"hospital", r"clinica", r"cl[ií]nica", r"medico", r"m[eé]dico",
        r"consulta", r"exame\b", r"laboratorio", r"laborat[oó]rio",
        r"drogasil", r"drogaraia", r"ultrafarma", r"onofre\b",
        r"gym\b", r"academia", r"smartfit", r"smart fit", r"bodytech",
        r"bluefit", r"fit\b.*academia", r"biolab", r"fleury\b",
        r"einstein\b", r"sirio", r"s[ií]rio", r"odonto", r"dentist",
        r"plano.*saude", r"sulamerica.*saude", r"amil\b", r"unimed\b",
        r"bradesco.*saude", r"hapvida", r"nossa saude",
    ]),
    (CategoryEnum.FARMACIA, [
        r"farmacia", r"farm[áa]cia", r"drogaria", r"drogist",
        r"drogas\b", r"panvel\b", r"nissei\b", r"farmavida",
        r"drogal\b", r"raia\b", r"pacheco\b", r"ultrafarma",
        r"pague menos", r"farmais", r"farmasil", r"droga raia",
        r"drog[ae]\b", r"medicat", r"precisa farma",
    ]),
    (CategoryEnum.EDUCACAO, [
        r"escola\b", r"colegio", r"col[eé]gio", r"universidade",
        r"faculdade", r"curso\b", r"udemy\b", r"coursera\b", r"alura\b",
        r"duolingo\b", r"rosetta\b", r"livro\b", r"livraria",
        r"saraiva\b", r"cultura\b.*livraria", r"amazon.*livro",
        r"material.*escolar", r"papelaria", r"ensino",
        r"linkedin.*learning", r"skillshare", r"pluralsight",
    ]),
    (CategoryEnum.ENTRETENIMENTO, [
        r"netflix\b", r"amazon.*prime", r"prime.*video", r"disney\+",
        r"disney plus", r"hbo\b", r"paramount\b", r"globoplay",
        r"spotify\b", r"deezer\b", r"apple.*music", r"youtube.*premium",
        r"cinema", r"cinemark", r"kinoplex", r"uci\b", r"cinesystem",
        r"teatro\b", r"show\b", r"ingresso", r"eventbrite",
        r"steam\b", r"playstation", r"xbox\b", r"nintendo\b",
        r"nuuvem\b", r"green man gaming", r"epic games",
        r"twitch\b", r"onlyfans",
    ]),
    (CategoryEnum.VESTUARIO, [
        r"renner\b", r"riachuelo", r"c&a\b", r"cea\b", r"hering\b",
        r"zara\b", r"h&m\b", r"forever 21", r"american eagle",
        r"nike\b", r"adidas\b", r"puma\b", r"asics\b", r"under armour",
        r"havaianas", r"crocs\b", r"netshoes", r"zattini\b",
        r"dafiti\b", r"centauro\b", r"decathlon", r"aramis\b",
        r"reserva\b", r"farm\b.*rio", r"osklen\b", r"ellus\b",
        r"calcados\b", r"cal[cç]ados", r"sapato\b", r"tenis\b.*loja",
    ]),
    (CategoryEnum.VIAGEM, [
        r"airbnb", r"booking\b", r"hotel\b", r"pousada", r"hostel\b",
        r"trivago\b", r"expedia\b", r"decolar\b", r"maxmilhas",
        r"latam.*viagens", r"cvc\b", r"submarino.*viagens",
        r"agencia.*viagem", r"turismo", r"passagem", r"aerea\b",
        r"delta\b.*air", r"american.*airlines", r"emirates\b",
    ]),
    (CategoryEnum.CASA, [
        r"leroy\b", r"leroymerlin", r"leroy merlin", r"telha norte",
        r"tok stok", r"tok&stok", r"etna\b", r"mobly\b", r"camicado",
        r"casa.*construcao", r"construcenter", r"casas bahia", r"magazine luiza",
        r"magazineluiza", r"magalu\b", r"americanas\b", r"submarino\b",
        r"condominio", r"agua\b.*luz", r"energia\b", r"copel\b",
        r"cemig\b", r"enel\b", r"comgas\b", r"sabesp\b", r"embasa\b",
        r"aluguel\b", r"iptu\b", r"agua.*esgoto",
    ]),
    (CategoryEnum.TECNOLOGIA, [
        r"apple\b", r"microsoft\b", r"google\b.*pay", r"amazon\b.*aws",
        r"digitalocean", r"heroku\b", r"github\b", r"icloud\b",
        r"dropbox\b", r"one drive", r"onedrive\b", r"adobe\b",
        r"autodesk\b", r"canva\b", r"figma\b",
        r"tim\b", r"claro\b", r"vivo\b", r"oi\b.*telecom",
        r"net\b.*internet", r"claro.*net", r"sky\b.*tv",
        r"internet\b", r"telefone\b", r"celular.*plano",
    ]),
    (CategoryEnum.SERVICOS, [
        r"seguro\b", r"banco\b.*tarifa", r"tarifa\b.*bancaria",
        r"anuidade\b", r"juros\b", r"multa\b",
        r"cartorio\b", r"cartório\b", r"governo\b",
        r"correios\b", r"fedex\b", r"dhl\b", r"sedex\b",
        r"lavanderia", r"tinturaria", r"cabeleireiro", r"barbeiro",
        r"salao\b", r"sal[ãa]o\b.*beleza", r"barbearia",
        r"manutencao", r"manutenção", r"eletricista", r"encanador",
    ]),
]


def classify(description: str) -> CategoryEnum:
    text = description.lower()
    text = re.sub(r"[*#@|]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    for category, patterns in CATEGORY_RULES:
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return category

    return CategoryEnum.OUTROS
