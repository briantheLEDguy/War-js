#include "WarNpcEquipment.h"
#include "WarRuntimeSettings.h"
#include "WarTypes.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"

namespace { const FName EquipmentTag(TEXT("WarNpcEquipment")); }

bool UWarNpcEquipmentLibrary::RequiresWeapons(FName Role)
{ return Role == TEXT("enemy") || Role == TEXT("guard") || Role == TEXT("marshal"); }

bool UWarNpcEquipmentLibrary::IsGeneratedAttachment(const UActorComponent* Component)
{ return Component && Component->HasAnyFlags(RF_Transient) && Component->ComponentHasTag(EquipmentTag); }

bool UWarNpcEquipmentCatalog::Resolve(FName Profile, FName Identity, FName Role,
    const FWarNpcLoadout*& Out, FString& Error) const
{
    Out = nullptr; Error.Reset();
    for (const auto& Row : Loadouts)
    {
        if (Row.Profile != Profile || Row.Role != Role || (!Row.Identities.IsEmpty() && !Row.Identities.Contains(Identity))) continue;
        if (Out) { Out = nullptr; Error = TEXT("Duplicate combat NPC loadout binding."); return false; }
        Out = &Row;
    }
    if (!Out) { Error = TEXT("No reviewed weapon loadout for this combat NPC."); return false; }
    if (Out->Body.IsNull() || !WarValidation::IsSha256(Out->BodySourceSha256)
        || (Out->Attachments.IsEmpty() && Out->EmbeddedWeaponMaterialSlots.IsEmpty()))
    { Out = nullptr; Error = TEXT("Combat NPC loadout lacks body provenance or equipment."); return false; }
    TSet<FName> Ids;
    for (const auto& Weapon : Out->Attachments)
    {
        const auto Scale = Weapon.RelativeTransform.GetScale3D();
        if (Weapon.Id.IsNone() || Ids.Contains(Weapon.Id) || Weapon.Bone.IsNone() || Weapon.Mesh.IsNull()
            || !WarValidation::IsSha256(Weapon.SourceSha256) || !Weapon.RelativeTransform.IsValid()
            || Scale.GetMin() <= 0 || Scale.GetMax() > 4)
        { Out = nullptr; Error = TEXT("Combat NPC weapon binding is incomplete or invalid."); return false; }
        Ids.Add(Weapon.Id);
    }
    return true;
}

bool UWarNpcEquipmentLibrary::Apply(USkeletalMeshComponent* Body, FName Profile, FName Identity,
    FName Role, FString& Error)
{
    Error.Reset();
    if (!RequiresWeapons(Role)) return true;
    auto* Catalog = GetDefault<UWarRuntimeSettings>()->NpcEquipmentCatalog.LoadSynchronous();
    const FWarNpcLoadout* Loadout = nullptr;
    if (!Body || !Body->GetOwner() || !Catalog || !Catalog->Resolve(Profile, Identity, Role, Loadout, Error))
    { if (Error.IsEmpty()) Error = TEXT("Combat NPC equipment catalog is unavailable."); return false; }
    if (!Body->GetSkeletalMeshAsset() || FSoftObjectPath(Body->GetSkeletalMeshAsset()) != Loadout->Body.ToSoftObjectPath())
    { Error = TEXT("Combat NPC body differs from the equipment binding."); return false; }
    for (const FName Slot : Loadout->EmbeddedWeaponMaterialSlots)
        if (Body->GetMaterialIndex(Slot) == INDEX_NONE || !Body->GetMaterial(Body->GetMaterialIndex(Slot)))
        { Error = TEXT("Authored embedded weapon is missing."); return false; }
    TArray<UStaticMesh*> LoadedMeshes;
    for (const auto& Weapon : Loadout->Attachments)
    {
        auto* Mesh = Weapon.Mesh.LoadSynchronous();
        if (!Body->DoesSocketExist(Weapon.Bone) || !Mesh || Mesh->GetStaticMaterials().IsEmpty())
        { Error = TEXT("Combat NPC weapon bone or materials are missing."); return false; }
        for (const auto& Material : Mesh->GetStaticMaterials())
            if (!Material.MaterialInterface) { Error = TEXT("Combat NPC weapon has a missing material."); return false; }
        LoadedMeshes.Add(Mesh);
    }
    // Validate the entire loadout before replacing anything. Re-entry cannot duplicate weapons.
    TInlineComponentArray<UStaticMeshComponent*> Previous; Body->GetOwner()->GetComponents(Previous);
    for (auto* Component : Previous)
        if (IsGeneratedAttachment(Component)) Component->DestroyComponent();
    for (int32 Index = 0; Index < Loadout->Attachments.Num(); ++Index)
    {
        const auto& Weapon = Loadout->Attachments[Index];
        auto* Component = NewObject<UStaticMeshComponent>(Body->GetOwner(), NAME_None, RF_Transient);
        Component->ComponentTags = {EquipmentTag, Weapon.Id};
        Component->SetStaticMesh(LoadedMeshes[Index]);
        Component->SetMobility(EComponentMobility::Movable);
        Component->SetCollisionProfileName(TEXT("NoCollision"));
        Component->SetGenerateOverlapEvents(false);
        Component->SetCanEverAffectNavigation(false);
        Component->SetupAttachment(Body, Weapon.Bone);
        Component->SetRelativeTransform(Weapon.RelativeTransform);
        Body->GetOwner()->AddInstanceComponent(Component);
        Component->RegisterComponent();
    }
    return true;
}
