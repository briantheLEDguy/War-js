using UnrealBuildTool;

public class AegisWarClientTarget : TargetRules
{
    public AegisWarClientTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Client;
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("AegisWar");
    }
}
