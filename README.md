## Melhorias no código atual
* Em cada trade, incluir informações adicionais no formato chave-valor. Por exemplo, podem ser inseridas informações de outros indicadores no momento da abertura do trade. Estas informações serão exibidas na rotina que imprime as informações de cada trade (uma linha por trade).
* Escrever uma rotina para imprimir e/ou salvar em CSV as informações de todos os trades de todos os dias (um trade por linha) com as informações adicionais inseridas no formato chave-valor.
A ideia aqui é ter uma tabela com todos os trades realizados na base de trading para poder fazer análises.

## Melhorias futuras
*	Pegar base de trading de TFs diferentes e unir na base de dados de TF menoros indicadores dos TF’s maiores. Exemplo, anexar o SQ e OBV do 2’, 5’, 10’, 15’, 30’, 60’
*	Incluir essa informação no arquivo de trades e fazer uma análise de quais modelos estatísticos podem ser aplicados com o objetivo de identificar quais variáveis e suas configurações têm maior peso para o trader ser vencedor. O objetivo é inferência.
    *	Aqui é preciso definir trade vencedor. Poder ser o que fez RR de 2:1 por exemplo.
