namespace Cidadela.Simulation;

/// <summary>
/// Decide os quadros de olhos e boca de um aldeão a partir da expressão e cuida do piscar: intervalo
/// aleatório entre <see cref="MinBlinkInterval"/> e <see cref="MaxBlinkInterval"/> segundos, semente fixa
/// pelo id (cada aldeão pisca no seu ritmo, sempre o mesmo), olhos fechados por <see cref="ClosedSeconds"/>.
/// Não pisca dormindo nem sonolento. C# puro: a view só lê <see cref="Eyes"/> e <see cref="Mouth"/>.
/// </summary>
public sealed class FaceAnimator
{
    public const float MinBlinkInterval = 2f;
    public const float MaxBlinkInterval = 6f;
    public const float ClosedSeconds = 0.12f;

    private readonly FaceTable _table;
    private uint _rng;
    private float _untilBlink;
    private float _closedLeft;

    /// <summary>Nome do quadro dos olhos a mostrar agora.</summary>
    public string Eyes { get; private set; }
    /// <summary>Nome do quadro da boca a mostrar agora.</summary>
    public string Mouth { get; private set; }
    /// <summary>Se os olhos estão fechados por um piscar.</summary>
    public bool Blinking => _closedLeft > 0f;

    public FaceAnimator(int id, FaceTable table)
    {
        _table = table;
        _rng = (uint)id * 2654435761u | 1u;
        _untilBlink = NextInterval();
        (Eyes, Mouth) = table.For(VillagerExpression.Distracted);
    }

    /// <summary>Avança o tempo e escolhe os quadros para a expressão dada.</summary>
    public void Advance(float dt, VillagerExpression expression)
    {
        (string eyes, string mouth) = _table.For(expression);
        Mouth = mouth;

        if (expression is VillagerExpression.Sleeping or VillagerExpression.Sleepy)
        {
            _closedLeft = 0f;
            Eyes = eyes;
            return;
        }

        if (_closedLeft > 0f)
        {
            _closedLeft -= dt;
        }
        else
        {
            _untilBlink -= dt;
            if (_untilBlink <= 0f)
            {
                _closedLeft = ClosedSeconds;
                _untilBlink = NextInterval();
            }
        }
        Eyes = _closedLeft > 0f ? _table.ClosedEyes : eyes;
    }

    private float NextInterval()
    {
        // xorshift32: determinístico e sem dependência da plataforma.
        _rng ^= _rng << 13;
        _rng ^= _rng >> 17;
        _rng ^= _rng << 5;
        float unit = (_rng & 0xFFFFFF) / (float)0x1000000;
        return MinBlinkInterval + unit * (MaxBlinkInterval - MinBlinkInterval);
    }
}
