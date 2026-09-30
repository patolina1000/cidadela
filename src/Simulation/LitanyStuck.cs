namespace Cidadela.Simulation;

/// <summary>
/// Por que o comando atual da ladainha travou (docs/ladainhas.md: "nunca travar calado"; a view diz em palavras do jogo).
/// </summary>
public enum LitanyStuck
{
    /// <summary>Sem caminho até o alvo.</summary>
    NoPath,
    /// <summary>O lugar citado não existe mais (a construção foi desmontada).</summary>
    NoPlace,
    /// <summary>Nenhum recurso daquele tipo dentro do raio (ou todos reservados por outros).</summary>
    NoResource,
    /// <summary>Mãos ocupadas com outro item (ou cheias) para pegar ou colher.</summary>
    HandsFull,
    /// <summary>Não tem o item na mão para pôr.</summary>
    HandsEmpty,
    /// <summary>O lugar não tem o item para pegar.</summary>
    SourceEmpty,
    /// <summary>O lugar está cheio (ou a máquina não aceita mais desse item).</summary>
    TargetFull,
    /// <summary>A máquina não usa esse item.</summary>
    NotAccepted,
    /// <summary>A construção não tem posto (não se opera).</summary>
    NoPost,
    /// <summary>Todos os postos da máquina já estão ocupados.</summary>
    PostTaken,
    /// <summary>Não aguenta o peso (carga zero para esse item).</summary>
    TooHeavy,
}
