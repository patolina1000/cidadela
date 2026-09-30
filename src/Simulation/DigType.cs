namespace Cidadela.Simulation;

/// <summary>Cavar a margem à mão ("digClay" em data/castellan.json): o item e quantos ticks por item; a margem não esgota.</summary>
public sealed record DigType(string Item, int Ticks);
