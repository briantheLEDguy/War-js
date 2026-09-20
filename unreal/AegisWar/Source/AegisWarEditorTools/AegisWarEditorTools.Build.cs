using UnrealBuildTool;

public class AegisWarEditorTools : ModuleRules
{
    public AegisWarEditorTools(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine" });
        PrivateDependencyModuleNames.AddRange(new[] { "UnrealEd", "MeshDescription", "StaticMeshDescription", "AssetRegistry", "RenderCore" });
    }
}
