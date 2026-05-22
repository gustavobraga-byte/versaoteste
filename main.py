import sys
import os
import random

REPO_URL = "https://github.com/gustavobraga-byte/PesquisAI.git"

SCIENCE_JOKES = [
    "🧪 E=mc²: Energia = Minha Paciência × Café²",
    "⚛️ Schrödinger espera que o download termine e não termine ao mesmo tempo.",
    "🔬 Olhar fixamente para a tela não acelera a instalação.",
    "⏳ No reino dos bytes, o tempo é relativo.",
    "🐌 Isso é mais lento que a difusão de um gás.",
    "👑 Se a paciência fosse um elemento, estaria no grupo dos nobres.",
    "🌡️ Estamos calculando o ponto de ebulição da sua paciência.",
    "🧮 O tempo de instalação é diretamente proporcional à sua vontade.",
    "🔭 A paciência é uma constante universal... ou quase.",
    "⚗️ Misturando paciência + expectativa = resultado em breve.",
    "⚡ Enquanto isso, um elétron ganha energia perdendo paciência.",
    "📐 A velocidade desse download quebra todas as leis da física.",
    "🌀 Seu progresso está em órbita: completa voltas e não chega ao fim.",
    "❄️ Mais lento que a água a 0°C: ainda não congelou, mas já está quase.",
    "🌋 A sua paciência está aumentando a entropia do universo.",
    "⚙️ Mais lento que a segunda lei da termodinâmica.",
    "🎯 De acordo com o princípio da incerteza: não sabemos quando termina.",
    "📊 Esse progresso está em equilíbrio estático: não se move.",
    "⚡ Velocidade menor que a luz, mas maior que a sua paciência.",
    "🌌 O universo expande mais rápido que esse download.",
    "🔋 A sua paciência é o verdadeiro motor desse processo.",
    "🧪 De acordo com a relatividade geral: o tempo passa mais devagar quando você espera.",
    "⚛️ Esse processo está em estado fundamental: não muda.",
    "📐 Força = massa × aceleração zero.",
    "🔬 Mais lento que a difusão.",
    "⚛️ Nesse ritmo, descobriremos o átomo de paciência.",
    "⚗️ Misturando H₂ + Paciência = H₂Wait₂O.",
    "🧪 Se a paciência fosse um metal, seria o mais estável da tabela.",
    "⚗️ Reação: Paciência(lento → Paciência + Cansaço",
    "🧪 Essa instalação é mais lenta que a precipitação.",
    "⚛️ Grupo 1, período 7: elemento Paciência.",
    "🧪 Número atômico da Paciência: ∞",
    "⚗️ O catalisador desse processo é o seu café.",
    "🧪 Ligação química: você e a paciência estão fortemente ligados agora.",
    "⚗️ Entalpia desse processo: muito alta.",
    "🧪 Solubilidade: a paciência está dissolvendo aos poucos.",
    "⚛️ Estado de oxidação da paciência: -1",
    "🧪 Essa velocidade é um gás nobre: não reage com nada.",
    "🧪 Se esse processo fosse uma reação, precisaria de muita energia de ativação.",
    "⚛️ Nesse ritmo, vamos descobrir o elemento 119: Esperâncio.",
    "🧪 A paciência é o novo solvente universal.",
    "⚗️ Mistura: 100% espera + 0% resultado.",
    "🧪 O pH da sua paciência está neutro... por enquanto.",
    "🧬 Se a evolução dependesse dessa velocidade, ainda seríamos amebas.",
    "🧫 Essa instalação está em período de incubação.",
    "🧬 Mais lento que a duplicação do DNA.",
    "🔬 Seu progresso está em metáfase: parado no meio.",
    "🧬 A paciência é o gene dominante nesse momento.",
    "🧫 Célula esperando: ciclo celular pausado na espera.",
    "🧬 Nesse ritmo, a fotossíntese é mais rápida.",
    "🔬 Mais lento que o transporte passivo.",
    "🧬 Se esse fosse um neurônio, a sinapse nunca chegaria.",
    "🧫 Essa espera é um organela sem mitocôndria: sem energia.",
    "🧬 Evolução: do download em curso há muito tempo.",
    "🧬 DNA: Descarga Nervosa Acelerada é o que falta.",
    "🧬 Meiose desse processo: divide e não termina.",
    "🧬 Nesse ritmo, as bactérias evoluiriam mais rápido.",
    "🧬 O ribossomo está traduzindo: esperando...",
    "🧮 A soma da sua paciência é maior que o número de Pi.",
    "📐 Esse progresso é uma série convergente para o infinito.",
    "🔢 Matematicamente, esse download tem complexidade O(infinito).",
    "📊 A probabilidade de terminar logo está se aproximando de zero.",
    "🧮 De acordo com o teorema do valor intermediário: existe um momento em que termina... talvez.",
    "📐 Esse processo é assintótico: chega perto mas nunca chega.",
    "🔢 A derivada desse progresso é zero: não muda.",
    "📊 A integral da sua paciência tende a infinito.",
    "🧮 1 + 1 = ainda esperando.",
    "📐 Esse download é um número irracional: não termina nunca.",
    "🔢 Complexidade Big O: O(muito devagar)",
    "📊 Estatisticamente, você tem 99% de chance de continuar esperar.",
    "🧮 Logaritmo dessa velocidade é negativo.",
    "📐 Progressão geométrica: razão menor que 1.",
    "🔢 Matemática do caos: não sabemos o que vem depois.",
    "💻 O algoritmo desse download é O(n²), onde n = sua paciência.",
    "⌨️ Mais lento que um bubble sort em 1 milhão de elementos.",
    "🔌 Esse processo está em modo economia de energia: muito economia.",
    "💾 O cache da sua paciência já está cheio.",
    "⌨️ Deadlock: você e o download estão esperando um pelo outro.",
    "🔄 Loop infinito: enquanto não terminar, você espera.",
    "💻 Pilha de espera: você está no fundo.",
    "🔌 Se esse fosse uma porta, seria a porta serial.",
    "💻 RAM: Realmente Aguardando Muito.",
    "⌨️ Compilando... há muito tempo.",
    "🔌 Mais lento que conexão discada.",
    "💻 Esse download é single thread: uma coisa de cada vez.",
    "⌨️ O buffer está cheio de paciência.",
    "🔌 HTTP: Hold On, Thinking Process.",
    "💻 Nesse ritmo, o USB 1.0 é supersônico.",
    "🌌 A luz do sol chega à Terra em 8 minutos. Esse download demora mais.",
    "🪐 A rotação da Terra é mais rápida.",
    "🌙 Mais lento que as fases da lua.",
    "🌌 O universo tem 13.8 bilhões de anos. Esse download parece mais velho.",
    "⭐ Constelação: Ursa Maior da Paciência",
    "🌘 Eclipse: enquanto isso, a lua já passou por todas as fases.",
    "🌌 Buraco negro: suga toda a sua paciência.",
    "🪐 Esse progresso está em órbita: completa voltas.",
    "🌌 Expansão do universo é mais rápida.",
    "⭐ Galáxia: Via Láctea da Espera",
    "🌌 Gravidade: está puxando sua paciência para baixo.",
    "🪐 Ano-luz: distância que o download percorre em um ano.",
]


def random_joke():
    return random.choice(SCIENCE_JOKES)


def ensure_in_colab():
    try:
        import google.colab
        return True
    except ImportError:
        return False


def show_loading_message():
    if ensure_in_colab():
        from IPython.display import display, HTML
        display(HTML("""
<style>
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
.loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
}
.spinner {
    width: 56px;
    height: 56px;
    border: 4px solid rgba(79, 195, 247, 0.12);
    border-top-color: #4fc3f7;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 24px;
}
.loading-text {
    color: #4fc3f7;
    font-family: monospace;
    font-size: 15px;
    animation: pulse 1.5s ease-in-out infinite;
}
</style>
<div class="loading-container">
    <div class="spinner"></div>
    <div class="loading-text">Carregando o PesquisAI...</div>
</div>
"""))
    else:
        print("⏳ Carregando o PesquisAI...")


def show_ready_message():
    if ensure_in_colab():
        from IPython.display import display, HTML
        display(HTML("""
<style>
@keyframes glow {
    0%, 100% { box-shadow: 0 0 20px rgba(93, 186, 126, 0.3); }
    50% { box-shadow: 0 0 40px rgba(93, 186, 126, 0.6); }
}
.ready-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 30px 20px 10px 20px;
}
.ready-badge {
    display: inline-flex;
    align-items: center;
    gap: 12px;
    padding: 16px 32px;
    background: rgba(93, 186, 126, 0.12);
    border: 2px solid rgba(93, 186, 126, 0.4);
    border-radius: 12px;
    animation: glow 2s ease-in-out infinite;
}
.ready-icon {
    font-size: 28px;
}
.ready-text {
    font-family: 'DM Mono', monospace;
    font-size: 18px;
    font-weight: 600;
    color: #5dba7e;
}
</style>
<div class="ready-container">
    <div class="ready-badge">
        <span class="ready-icon">✨</span>
        <span class="ready-text">PesquisAI pronto!</span>
    </div>
</div>
"""))
    else:
        print("\n✨ PesquisAI pronto!\n")


def run():
    show_loading_message()
    
    print("\n" + "="*50)
    print("  🚀 INICIANDO PESQUISAI")
    print("="*50 + "\n")
    
    print(random_joke())
    from setup_dependencies import run_all as setup_deps
    setup_deps()
    
    print("\n" + random_joke())
    from setup_skills import install_skills
    install_skills()
    
    print("\n" + random_joke())
    from setup_drive import mount_drive, get_drive_info
    folder_path, drive_url = mount_drive()
    
    print("\n" + random_joke())
    from launch_app import launch, set_drive_info
    set_drive_info(folder_path, drive_url)
    
    show_ready_message()
    launch()


if __name__ == "__main__":
    run()
