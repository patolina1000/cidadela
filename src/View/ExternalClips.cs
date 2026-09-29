using System.Collections.Generic;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Acrescenta ao AnimationPlayer de um corpo os clipes de um GLB separado, que só tem esqueleto e animação com os
/// mesmos nomes de osso (ex.: assets/modelos/prova_operacao/variante_r06/clipes/girar_roda.glb). Os clipes entram
/// como uma AnimationLibrary nova ("biblioteca/clipe"), sem mexer no GLB do corpo. Nome com sufixo "-loop" perde
/// o sufixo e ganha loop (o importador do Godot costuma fazer isso antes; aqui vale para os dois casos).
/// As trilhas são redirecionadas para o esqueleto do corpo; as de posição são convertidas pela razão entre a
/// escala do esqueleto do clipe e a do corpo (um clipe exportado com a Armature em 0,004 serve num corpo em metros).
/// Duração do ciclo: o exportador do Blender põe o quadro 1 em 1/24 s e o importador do Godot reamostra a partir de
/// 0 (a 30 fps), então o clipe importado fica um quadro mais longo, com o começo parado. Quando a duração real é
/// informada (clipes.json da arte), o começo é cortado: o clipe passa a começar no primeiro quadro e durar um ciclo.
/// </summary>
public static class ExternalClips
{
    private const string LoopSuffix = "-loop";

    /// <summary>Carrega o GLB de clipes e o acrescenta ao player; devolve os nomes completos ("biblioteca/clipe").</summary>
    public static List<string> AddLibrary(AnimationPlayer player, string glbPath, string libraryName,
        IReadOnlyDictionary<string, float>? durations = null)
    {
        var added = new List<string>();
        if (GD.Load<PackedScene>(glbPath) is not PackedScene scene)
        {
            GD.PushWarning($"Clipes: não achei {glbPath}.");
            return added;
        }
        Node3D clipRoot = scene.Instantiate<Node3D>();
        try
        {
            AnimationPlayer? clipPlayer = First<AnimationPlayer>(clipRoot);
            Skeleton3D? clipSkeleton = First<Skeleton3D>(clipRoot);
            Node? bodyRoot = player.GetNodeOrNull(player.RootNode);
            Skeleton3D? bodySkeleton = bodyRoot is null ? null : First<Skeleton3D>(bodyRoot);
            if (clipPlayer is null || clipSkeleton is null || bodyRoot is null || bodySkeleton is null)
            {
                GD.PushWarning($"Clipes: {glbPath} ou o corpo não têm AnimationPlayer e Skeleton3D.");
                return added;
            }

            Node clipPlayerRoot = clipPlayer.GetNode(clipPlayer.RootNode);
            string clipSkeletonPath = clipPlayerRoot.GetPathTo(clipSkeleton).ToString();
            NodePath bodySkeletonPath = bodyRoot.GetPathTo(bodySkeleton);
            float positionFactor = ScaleUpTo(clipSkeleton, clipPlayerRoot) / ScaleUpTo(bodySkeleton, bodyRoot);

            var library = new AnimationLibrary();
            foreach (StringName name in clipPlayer.GetAnimationList())
            {
                string clipName = name.ToString();
                if (clipName == "RESET")
                    continue;
                var animation = (Animation)clipPlayer.GetAnimation(name).Duplicate(true);
                float duration = 0f;
                if (durations is not null && !durations.TryGetValue(clipName, out duration))
                    durations.TryGetValue(clipName + LoopSuffix, out duration);
                if (clipName.EndsWith(LoopSuffix))
                {
                    clipName = clipName[..^LoopSuffix.Length];
                    animation.LoopMode = Animation.LoopModeEnum.Linear;
                }
                Retarget(animation, clipSkeletonPath, bodySkeletonPath, bodySkeleton, positionFactor, glbPath);
                if (duration > 0f)
                    TrimStart(animation, duration);
                library.AddAnimation(clipName, animation);
                added.Add($"{libraryName}/{clipName}");
            }
            if (player.HasAnimationLibrary(libraryName))
                player.RemoveAnimationLibrary(libraryName);
            player.AddAnimationLibrary(libraryName, library);
            return added;
        }
        finally
        {
            clipRoot.Free();
        }
    }

    private static void Retarget(Animation animation, string clipSkeletonPath, NodePath bodySkeletonPath, Skeleton3D bodySkeleton,
        float positionFactor, string source)
    {
        for (int t = animation.GetTrackCount() - 1; t >= 0; t--)
        {
            NodePath path = animation.TrackGetPath(t);
            string node = path.GetConcatenatedNames().ToString();
            string bone = path.GetConcatenatedSubNames().ToString();
            if (node != clipSkeletonPath || bone.Length == 0 || bodySkeleton.FindBone(bone) < 0)
            {
                GD.PushWarning($"Clipes: trilha {path} de {source} não tem osso no corpo; removida.");
                animation.RemoveTrack(t);
                continue;
            }
            animation.TrackSetPath(t, new NodePath($"{bodySkeletonPath}:{bone}"));
            if (animation.TrackGetType(t) == Animation.TrackType.Position3D && !Mathf.IsEqualApprox(positionFactor, 1f))
            {
                for (int k = 0; k < animation.TrackGetKeyCount(t); k++)
                    animation.TrackSetKeyValue(t, k, (Vector3)animation.TrackGetKeyValue(t, k) * positionFactor);
            }
        }
    }

    /// <summary>
    /// Corta o começo do clipe para ele durar <paramref name="duration"/>: cada trilha recebe uma chave no novo
    /// começo (o valor interpolado ali) e as chaves seguintes são deslocadas.
    /// </summary>
    private static void TrimStart(Animation animation, float duration)
    {
        double offset = animation.Length - duration;
        if (offset <= 1e-5)
            return;
        for (int t = 0; t < animation.GetTrackCount(); t++)
        {
            Animation.TrackType type = animation.TrackGetType(t);
            if (type is not (Animation.TrackType.Position3D or Animation.TrackType.Rotation3D or Animation.TrackType.Scale3D))
                continue;
            Variant atStart = type switch
            {
                Animation.TrackType.Position3D => animation.PositionTrackInterpolate(t, offset),
                Animation.TrackType.Rotation3D => animation.RotationTrackInterpolate(t, offset),
                _ => animation.ScaleTrackInterpolate(t, offset),
            };
            var keys = new List<(double Time, Variant Value)> { (0.0, atStart) };
            for (int k = 0; k < animation.TrackGetKeyCount(t); k++)
            {
                double time = animation.TrackGetKeyTime(t, k) - offset;
                if (time > 1e-6)
                    keys.Add((time, animation.TrackGetKeyValue(t, k)));
            }
            while (animation.TrackGetKeyCount(t) > 0)
                animation.TrackRemoveKey(t, 0);
            foreach ((double time, Variant value) in keys)
                animation.TrackInsertKey(t, time, value);
        }
        animation.Length = duration;
    }

    /// <summary>Escala uniforme acumulada do nó até o ancestral (o Armature do glTF costuma levar a escala).</summary>
    private static float ScaleUpTo(Node3D node, Node ancestor)
    {
        Transform3D t = Transform3D.Identity;
        for (Node n = node; n != ancestor && n is Node3D n3; n = n.GetParent())
            t = n3.Transform * t;
        return t.Basis.Scale.X;
    }

    private static T? First<T>(Node root) where T : Node
    {
        if (root is T self)
            return self;
        foreach (Node child in root.FindChildren("*", typeof(T).Name, recursive: true, owned: false))
            return (T)child;
        return null;
    }
}
