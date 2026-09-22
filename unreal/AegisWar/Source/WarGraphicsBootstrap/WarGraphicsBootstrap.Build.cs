using UnrealBuildTool;

public class WarGraphicsBootstrap : ModuleRules
{
    public WarGraphicsBootstrap(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PrivateDependencyModuleNames.AddRange(new[] { "Core" });
    }
}
