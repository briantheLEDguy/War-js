using UnrealBuildTool;

public class AegisWar : ModuleRules
{
    public AegisWar(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] {
            "Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput",
            "GameplayAbilities", "GameplayTags", "GameplayTasks", "DeveloperSettings",
            "UMG", "OnlineSubsystem", "OnlineSubsystemUtils", "ProceduralMeshComponent", "AIModule", "NavigationSystem"
        });
        PrivateDependencyModuleNames.AddRange(new[] { "Json", "JsonUtilities", "Slate", "SlateCore", "ApplicationCore", "WarGraphicsBootstrap", "HTTP", "Sockets", "RHI", "RenderCore", "Renderer", "PhysicsCore", "Chaos", "ChaosCore", "PlatformCrypto", "PlatformCryptoContext" });
        // Private, version-bound diagnostics read the renderer's final view rect.
        PrivateIncludePaths.Add(System.IO.Path.Combine(GetModuleDirectory("Renderer"), "Private"));
        PrivateIncludePaths.Add(System.IO.Path.Combine(GetModuleDirectory("Renderer"), "Internal"));
        if (Target.Platform == UnrealTargetPlatform.Win64 || Target.Platform == UnrealTargetPlatform.Linux
            || Target.Platform == UnrealTargetPlatform.Mac)
        {
            DynamicallyLoadedModuleNames.Add("OnlineSubsystemSteam");
        }
    }
}
