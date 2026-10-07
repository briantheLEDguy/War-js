using UnrealBuildTool;

public class AegisWarEditorTools : ModuleRules
{
    public AegisWarEditorTools(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine" });
        PrivateDependencyModuleNames.AddRange(new[] { "AegisWar", "UnrealEd", "MeshDescription", "StaticMeshDescription", "AssetRegistry", "RenderCore", "RHI", "MeshUtilities", "NavigationSystem", "PhysicsCore", "Json", "JsonUtilities" });
        if (Target.bCompileRecast) PrivateDependencyModuleNames.Add("Navmesh");
    }
}
