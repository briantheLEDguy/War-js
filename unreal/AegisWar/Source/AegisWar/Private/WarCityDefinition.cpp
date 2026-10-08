#include "WarCityDefinition.h"
#include "Engine/Level.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/Light.h"
#include "Engine/ReflectionCapture.h"
#include "Engine/SkyLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/VolumetricCloudComponent.h"
#include "Engine/Brush.h"
#include "Engine/BlockingVolume.h"
#include "Engine/LevelScriptActor.h"
#include "GameFramework/WorldSettings.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInterface.h"

bool UWarCityDefinition::Validate(FString& Error) const
{
    if ((ZoneId != TEXT("aegis_capital") && ZoneId != TEXT("riftspire_capital"))
        || Origin.ContainsNaN() || Revision.IsEmpty() || SceneryLevels.IsEmpty())
    { Error = TEXT("Shared city definition is incomplete. Restore city content and retry."); return false; }
    TSet<FName> Seen;
    for (const auto& Level : SceneryLevels)
    {
        const FString Package = Level.ToSoftObjectPath().GetLongPackageName();
        if (!Package.StartsWith(TEXT("/Game/")) || Seen.Contains(FName(*Package)))
        { Error = TEXT("Shared city scenery is missing or attached twice."); return false; }
        Seen.Add(FName(*Package));
    }
    Error.Reset(); return true;
}

TArray<FName> UWarCityDefinition::Packages() const
{
    TArray<FName> Result;
    for (const auto& Level : SceneryLevels) Result.Add(FName(*Level.ToSoftObjectPath().GetLongPackageName()));
    return Result;
}

bool UWarCityDefinition::IsSceneryActor(const AActor* Actor)
{
    // Exact native classes prevent a gameplay Blueprint from entering the presentation world.
    if (!Actor) return true;
    const UClass* Class = Actor->GetClass();
    if (Class->HasAnyClassFlags(CLASS_CompiledFromBlueprint)) return false;
    return Class == AStaticMeshActor::StaticClass() || Actor->IsA<ALight>()
        || Class == ASkyLight::StaticClass() || Actor->IsA<AReflectionCapture>()
        || Class == AExponentialHeightFog::StaticClass() || Class == ASkyAtmosphere::StaticClass()
        || Class == AVolumetricCloud::StaticClass()
        || Class == APostProcessVolume::StaticClass() || Class == ABlockingVolume::StaticClass()
        || Class == AWorldSettings::StaticClass() || Class == ALevelScriptActor::StaticClass()
        || (Actor->GetLevel() && Actor == Actor->GetLevel()->GetDefaultBrush());
}

bool UWarCityDefinition::ValidateLevel(const ULevel* Level, FString& Error)
{
    if (!Level) { Error = TEXT("Shared city level is unavailable."); return false; }
    for (const AActor* Actor : Level->Actors)
    {
        if (!IsSceneryActor(Actor))
        { Error = TEXT("Shared city scenery contains a gameplay actor: ") + Actor->GetName(); return false; }
        if (!Actor) continue;
        TInlineComponentArray<UStaticMeshComponent*> Meshes; Actor->GetComponents(Meshes);
        for (const auto* Mesh : Meshes)
        {
            if (!Mesh->IsVisible() || Mesh->bHiddenInGame) continue;
            if (!Mesh->GetStaticMesh() || !Mesh->GetStaticMesh()->GetPathName().StartsWith(TEXT("/Game/")))
            { Error = TEXT("Shared city model is missing or is a primitive substitute."); return false; }
            for (int32 I = 0; I < Mesh->GetNumMaterials(); ++I)
                if (!Mesh->GetMaterial(I))
                { Error = TEXT("Shared city material is missing."); return false; }
        }
    }
    Error.Reset(); return true;
}
