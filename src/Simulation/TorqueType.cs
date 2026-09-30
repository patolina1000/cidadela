namespace Cidadela.Simulation;

/// <summary>
/// Parte de uma rede de torque ("torque" em data/buildings.json; docs/cadeia_flecha.md). A construção liga a rotação às
/// 4 vizinhas que também têm torque. <paramref name="Supply"/>: força que ela dá (roda d'água); <paramref name="Demand"/>:
/// força que consome (fole, manivela); <paramref name="SpeedBonus"/>: multiplicador da receita com a rede girando
/// (o fole da fundição: 1,5); 1 = nenhum. Tudo zero: só conduz (o eixo).
/// </summary>
public sealed record TorqueType(float Supply, float Demand, float SpeedBonus);
