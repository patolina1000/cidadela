namespace Cidadela.Simulation;

/// <summary>
/// Peso de um item ("peso" em data/items.json; docs/linha_energia.md, regra 3). Pesado: só nas costas, nunca em esteira
/// nem em mariposa. Leve: esteira e mariposa (nas costas também, mas ineficiente). Médio está em aberto: o jogo recusa.
/// </summary>
public enum ItemWeight
{
    Heavy,
    Light,
}
