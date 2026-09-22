#include "WarContentSubsystem.h"
#include "WarEnemyRules.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"

bool UWarContentSubsystem::ValidateWorldVisual(FName Purpose, FName ZoneId, FName EntityId,
    FName VisualPropId, const UStaticMeshComponent* Component, FString& Error) const
{
    Error = WorldVisualError;
    if (!Error.IsEmpty()) return false;
    const auto* Binding = WorldVisuals.Find(WarWorldVisuals::Key(Purpose, ZoneId, EntityId));
    if (Purpose == TEXT("training_dummy"))
    {
        FWarEnemyDefinition Definition;
        if (!Binding || !WarEnemies::Parse(GetInterfaceCatalogSource(), ZoneId, EntityId, Definition, Error)
            || !Definition.bTrainingDummy || Binding->SourceModel != Definition.StaticModel)
        { Error = TEXT("Training target does not use its exact source dummy model."); return false; }
    }
    const UStaticMesh* Mesh = Component ? Component->GetStaticMesh() : nullptr;
    TArray<FString> Materials;
    if (Component)
        for (int32 Index = 0; Index < Component->GetNumMaterials(); ++Index)
        {
            const auto* Material = Component->GetMaterial(Index);
            Materials.Add(Material ? Material->GetPathName() : FString());
        }
    if (UE_BUILD_SHIPPING || !Binding || !Mesh || !WarWorldVisuals::Matches(*Binding, VisualPropId,
        Mesh->GetPathName(), Materials, Component->GetCollisionProfileName()))
    {
        Error = TEXT("This world object's mesh, materials or collision differ from its reviewed binding.");
        return false;
    }
    Error.Reset(); return true;
}
