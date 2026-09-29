using System.Collections.Generic;
using System.Globalization;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Acrescenta ao AnimationPlayer de um corpo os clipes de um GLB separado, só com esqueleto e animação
/// (docs/animacao_contrato.md, "CLIPES NOVOS"). Os clipes entram como uma AnimationLibrary nova
/// ("biblioteca/clipe"), sem mexer no GLB do corpo; nome com sufixo "-loop" perde o sufixo e ganha loop.
/// Modo estrito ("O JOGO É ESTRITO"): o clipe é recusado, com aviso, se o esqueleto dele tiver escala diferente da
/// do corpo, ossos diferentes, repouso diferente em mais de 0,01 mm, ou se a primeira chave não estiver em t = 0.
/// O importador do Godot (e o GLTFDocument) sempre recria a primeira chave em t = 0, segurando o primeiro quadro;
/// um clipe exportado com o começo atrasado aparece então como um clipe mais longo. Por isso, quando a duração do
/// clipes.json é informada, o clipe também é recusado se durar mais de meio quadro a mais ou a menos.
/// Nada é convertido nem cortado.
/// </summary>
public static class ExternalClips
{
    private const string LoopSuffix = "-loop";
    private const float MaxRestDiffMm = 0.01f;
    private const float ScaleTolerance = 1e-4f;
    private const double FirstKeyTolerance = 1e-4;

    /// <summary>Carrega o GLB de clipes e o acrescenta ao player; devolve os nomes completos ("biblioteca/clipe").</summary>
    public static List<string> AddLibrary(AnimationPlayer player, string glbPath, string libraryName,
        IReadOnlyDictionary<string, float>? durations = null)
    {
        if (GD.Load<PackedScene>(glbPath) is not PackedScene scene)
        {
            GD.PushWarning($"Clipes: não achei {glbPath}.");
            return new List<string>();
        }
        Node3D clipRoot = scene.Instantiate<Node3D>();
        try
        {
            return AddLibrary(player, clipRoot, glbPath, libraryName, durations);
        }
        finally
        {
            clipRoot.Free();
        }
    }

    /// <summary>Mesmo que o outro, com a cena do GLB já instanciada (ex.: lida em tempo de execução por GLTFDocument).</summary>
    public static List<string> AddLibrary(AnimationPlayer player, Node clipRoot, string source, string libraryName,
        IReadOnlyDictionary<string, float>? durations = null)
    {
        var added = new List<string>();
        AnimationPlayer? clipPlayer = First<AnimationPlayer>(clipRoot);
        Skeleton3D? clipSkeleton = First<Skeleton3D>(clipRoot);
        Node? bodyRoot = player.GetNodeOrNull(player.RootNode);
        Skeleton3D? bodySkeleton = bodyRoot is null ? null : First<Skeleton3D>(bodyRoot);
        if (clipPlayer is null || clipSkeleton is null || bodyRoot is null || bodySkeleton is null)
        {
            GD.PushWarning($"Clipes recusados: {source} ou o corpo não têm AnimationPlayer e Skeleton3D.");
            return added;
        }
        Node clipPlayerRoot = clipPlayer.GetNode(clipPlayer.RootNode);

        var problems = new List<string>();
        CheckSkeleton(clipSkeleton, clipPlayerRoot, bodySkeleton, bodyRoot, problems);
        var animations = new List<(string Name, Animation Animation)>();
        foreach (StringName name in clipPlayer.GetAnimationList())
        {
            if (name == "RESET")
                continue;
            Animation animation = clipPlayer.GetAnimation(name);
            double first = FirstKeyTime(animation);
            if (first > FirstKeyTolerance)
                problems.Add($"o clipe \"{name}\" começa em t = {F(first, "0.0000")} s (tem que ser 0)");
            if (durations is not null && (durations.TryGetValue(name.ToString(), out float expected)
                    || durations.TryGetValue(name + LoopSuffix, out expected)) && expected > 0f)
            {
                double tolerance = HalfFrame(animation);
                if (System.Math.Abs(animation.Length - expected) > tolerance)
                    problems.Add($"o clipe \"{name}\" dura {F(animation.Length, "0.0000")} s e o clipes.json diz {F(expected, "0.0000")} s " +
                        "(começo atrasado ou fim a mais; a primeira chave tem que estar em t = 0)");
            }
            animations.Add((name.ToString(), animation));
        }
        if (problems.Count > 0)
        {
            GD.PushWarning($"Clipes recusados: {source} fora do contrato de animação: {string.Join("; ", problems)}.");
            return added;
        }

        string clipSkeletonPath = clipPlayerRoot.GetPathTo(clipSkeleton).ToString();
        NodePath bodySkeletonPath = bodyRoot.GetPathTo(bodySkeleton);
        var library = new AnimationLibrary();
        foreach ((string name, Animation original) in animations)
        {
            string clipName = name;
            var animation = (Animation)original.Duplicate(true);
            if (clipName.EndsWith(LoopSuffix))
            {
                clipName = clipName[..^LoopSuffix.Length];
                animation.LoopMode = Animation.LoopModeEnum.Linear;
            }
            Retarget(animation, clipSkeletonPath, bodySkeletonPath, bodySkeleton, source);
            library.AddAnimation(clipName, animation);
            added.Add($"{libraryName}/{clipName}");
        }
        if (player.HasAnimationLibrary(libraryName))
            player.RemoveAnimationLibrary(libraryName);
        player.AddAnimationLibrary(libraryName, library);
        return added;
    }

    /// <summary>Escala, ossos e repouso do esqueleto do clipe contra os do corpo, cada um no espaço da sua raiz.</summary>
    private static void CheckSkeleton(Skeleton3D clip, Node clipRoot, Skeleton3D body, Node bodyRoot, List<string> problems)
    {
        Transform3D clipToRoot = UpTo(clip, clipRoot), bodyToRoot = UpTo(body, bodyRoot);
        float clipScale = clipToRoot.Basis.Scale.X, bodyScale = bodyToRoot.Basis.Scale.X;
        if (Mathf.Abs(clipScale - bodyScale) > ScaleTolerance * Mathf.Max(1f, bodyScale))
            problems.Add($"Armature em escala {F(clipScale, "0.####")} (corpo: {F(bodyScale, "0.####")})");

        var missing = new List<string>();
        float worst = 0f;
        string worstBone = "";
        for (int b = 0; b < body.GetBoneCount(); b++)
        {
            string bone = body.GetBoneName(b);
            int c = clip.FindBone(bone);
            if (c < 0)
            {
                missing.Add(bone);
                continue;
            }
            float mm = (clipToRoot * clip.GetBoneGlobalRest(c).Origin).DistanceTo(bodyToRoot * body.GetBoneGlobalRest(b).Origin) * 1000f;
            if (mm > worst)
                (worst, worstBone) = (mm, bone);
        }
        if (missing.Count > 0 || clip.GetBoneCount() != body.GetBoneCount())
            problems.Add($"ossos diferentes do corpo ({clip.GetBoneCount()} no clipe, {body.GetBoneCount()} no corpo; faltam: {string.Join(", ", missing)})");
        if (worst > MaxRestDiffMm)
            problems.Add($"repouso difere {F(worst, "0.###")} mm no osso {worstBone} (limite {F(MaxRestDiffMm, "0.00")} mm)");
    }

    private static void Retarget(Animation animation, string clipSkeletonPath, NodePath bodySkeletonPath, Skeleton3D bodySkeleton, string source)
    {
        for (int t = animation.GetTrackCount() - 1; t >= 0; t--)
        {
            NodePath path = animation.TrackGetPath(t);
            string node = path.GetConcatenatedNames().ToString();
            string bone = path.GetConcatenatedSubNames().ToString();
            if (node != clipSkeletonPath || bone.Length == 0 || bodySkeleton.FindBone(bone) < 0)
            {
                GD.PushWarning($"Clipes: trilha {path} de {source} não é de um osso do corpo; removida.");
                animation.RemoveTrack(t);
                continue;
            }
            animation.TrackSetPath(t, new NodePath($"{bodySkeletonPath}:{bone}"));
        }
    }

    /// <summary>Meio intervalo entre as duas primeiras chaves da trilha mais densa (meio quadro).</summary>
    private static double HalfFrame(Animation animation)
    {
        double step = double.MaxValue;
        for (int t = 0; t < animation.GetTrackCount(); t++)
            if (animation.TrackGetKeyCount(t) > 1)
                step = System.Math.Min(step, animation.TrackGetKeyTime(t, 1) - animation.TrackGetKeyTime(t, 0));
        return step == double.MaxValue ? 1.0 / 48.0 : step / 2.0;
    }

    private static double FirstKeyTime(Animation animation)
    {
        double first = double.MaxValue;
        for (int t = 0; t < animation.GetTrackCount(); t++)
            if (animation.TrackGetKeyCount(t) > 0)
                first = System.Math.Min(first, animation.TrackGetKeyTime(t, 0));
        return first == double.MaxValue ? 0.0 : first;
    }

    /// <summary>Transformação acumulada do nó até o ancestral (o Armature do glTF leva a escala, se houver).</summary>
    private static Transform3D UpTo(Node3D node, Node ancestor)
    {
        Transform3D t = Transform3D.Identity;
        for (Node n = node; n != ancestor && n is Node3D n3; n = n.GetParent())
            t = n3.Transform * t;
        return t;
    }

    private static string F(double value, string format) => value.ToString(format, CultureInfo.GetCultureInfo("pt-BR"));

    private static T? First<T>(Node root) where T : Node
    {
        if (root is T self)
            return self;
        foreach (Node child in root.FindChildren("*", typeof(T).Name, recursive: true, owned: false))
            return (T)child;
        return null;
    }
}
