#include "WarCharacterVisualDefinition.h"
#include "Animation/AnimBlueprintGeneratedClass.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Engine/SkeletalMesh.h"
#if WITH_EDITOR
#include "Misc/DataValidation.h"
#endif

bool UWarCharacterVisualDefinition::ValidateForSpawn(const EWarRealm ExpectedRealm, FString& OutError) const
{
    const auto Reject = [&OutError](const TCHAR* Message) { OutError = Message; return false; };
    OutError.Reset();
    if (ProfileKey.IsNone() || RaceId.IsNone() || ClassId.IsNone() || BodyVariant.IsNone())
        return Reject(TEXT("Character visual identity is incomplete."));
    if (Realm == EWarRealm::None || Realm != ExpectedRealm)
        return Reject(TEXT("Character visual does not match its server-assigned realm."));
    if (!bComplexAuthoredModel || SourceModel.IsEmpty() || !WarValidation::IsSha256(SourceSha256))
        return Reject(TEXT("Character visual requires authored-model provenance and source SHA-256."));
    if (SourceModel.Contains(TEXT("primitive"), ESearchCase::IgnoreCase)
        || SourceModel.Contains(TEXT("proxy"), ESearchCase::IgnoreCase))
        return Reject(TEXT("Primitive and proxy character sources are prohibited."));
    if (!SkeletalMesh.ToSoftObjectPath().GetLongPackageName().StartsWith(TEXT("/Game/")))
        return Reject(TEXT("Character mesh must be an imported project asset."));
    USkeletalMesh* Mesh = SkeletalMesh.LoadSynchronous();
    if (!Mesh || !Mesh->GetSkeleton() || Mesh->GetRefSkeleton().GetNum() < 2 || Mesh->GetLODNum() < 1)
        return Reject(TEXT("Character mesh is missing, unrigged, or has no imported LOD."));
    if (Mesh->GetMaterials().IsEmpty()) return Reject(TEXT("Character mesh has no authored materials."));
    for (const FSkeletalMaterial& Material : Mesh->GetMaterials())
    {
        if (!Material.MaterialInterface) return Reject(TEXT("Character mesh contains an unassigned material."));
    }
    if (MeshTransform.ContainsNaN() || MeshTransform.GetScale3D().GetMin() <= 0.f)
        return Reject(TEXT("Character mesh transform is invalid."));
    if (!AnimationBlueprint.IsNull())
    {
        const UAnimBlueprintGeneratedClass* AnimationClass = Cast<UAnimBlueprintGeneratedClass>(AnimationBlueprint.LoadSynchronous());
        if (!AnimationClass || AnimationClass->GetTargetSkeleton() != Mesh->GetSkeleton())
            return Reject(TEXT("Animation Blueprint must use the imported character skeleton."));
    }
    else
    {
        const UAnimSequence* Idle = IdleAnimation.LoadSynchronous();
        if (!Idle || Idle->GetSkeleton() != Mesh->GetSkeleton())
            return Reject(TEXT("Character needs a matching Animation Blueprint or imported idle sequence."));
    }
    return true;
}

FPrimaryAssetId UWarCharacterVisualDefinition::GetPrimaryAssetId() const
{
    return FPrimaryAssetId(TEXT("WarCharacterVisual"), ProfileKey);
}

#if WITH_EDITOR
EDataValidationResult UWarCharacterVisualDefinition::IsDataValid(FDataValidationContext& Context) const
{
    FString Error;
    if (!ValidateForSpawn(Realm, Error))
    {
        Context.AddError(FText::FromString(Error));
        return EDataValidationResult::Invalid;
    }
    return EDataValidationResult::Valid;
}
#endif
