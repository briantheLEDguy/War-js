using UnrealBuildTool;

public class AegisWar : ModuleRules
{
    public AegisWar(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] {
            "Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput",
            "GameplayAbilities", "GameplayTags", "GameplayTasks", "DeveloperSettings",
            "UMG", "OnlineSubsystem", "OnlineSubsystemUtils", "ProceduralMeshComponent"
        });
        PrivateDependencyModuleNames.AddRange(new[] { "Json", "JsonUtilities", "Slate", "SlateCore", "ApplicationCore", "WarGraphicsBootstrap" });
        if (Target.Platform == UnrealTargetPlatform.Win64 || Target.Platform == UnrealTargetPlatform.Linux
            || Target.Platform == UnrealTargetPlatform.Mac)
        {
            DynamicallyLoadedModuleNames.Add("OnlineSubsystemSteam");
        }
    }
}
