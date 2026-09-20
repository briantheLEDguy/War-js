using UnrealBuildTool;

[SupportedPlatforms(UnrealPlatformClass.Server)]
public class AegisWarServerTarget : TargetRules
{
    public AegisWarServerTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Server;
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("AegisWar");
    }
}
