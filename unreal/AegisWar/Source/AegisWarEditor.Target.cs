using UnrealBuildTool;

public class AegisWarEditorTarget : TargetRules
{
    public AegisWarEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("AegisWar");
    }
}
