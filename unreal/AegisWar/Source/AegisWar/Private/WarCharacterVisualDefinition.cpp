#include "WarCharacterVisualDefinition.h"
#include "Animation/AnimBlueprintGeneratedClass.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
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
        for (const FName Required : { FName(TEXT("walk")), FName(TEXT("run")), FName(TEXT("jump")), FName(TEXT("death")), FName(TEXT("attack_melee")) })
        {
            if (!ImportedAnimations.Contains(Required)) return Reject(TEXT("Character is missing an imported movement/combat animation."));
        }
    }
    for (const auto& Entry : ImportedAnimations)
    {
        const UAnimSequence* Animation = Entry.Value.LoadSynchronous();
        if (!Animation || Animation->GetSkeleton() != Mesh->GetSkeleton())
            return Reject(TEXT("Character animation set contains a missing or incompatible sequence."));
    }
    if (!AnimationStyle.IsNone())
    {
        const UAnimSequence* Basic = ImportedAnimations.FindRef(TEXT("attack_melee")).LoadSynchronous();
        if (!Basic || !FMath::IsFinite(BasicContactSeconds) || BasicContactSeconds <= 0 || BasicContactSeconds >= Basic->GetPlayLength())
            return Reject(TEXT("Basic attack requires an authored contact inside its recovery duration."));
        for (FName Required : {FName(TEXT("idle")), FName(TEXT("walk_backward")), FName(TEXT("strafe_left")), FName(TEXT("strafe_right")),
            FName(TEXT("turn_left")), FName(TEXT("turn_right")), FName(TEXT("hit_front")), FName(TEXT("hit_back")), FName(TEXT("landing"))})
            if (!ImportedAnimations.Contains(Required)) return Reject(TEXT("Native animation states are incomplete."));
        const bool bPlayable = ProfileKey == TEXT("civic_battle_prelate_m") || ProfileKey == TEXT("civic_sunfire_templar_m")
            || ProfileKey == TEXT("civic_ember_arcanist_m") || ProfileKey == TEXT("mire_warbrute_m");
        if (bPlayable && AbilityPresentations.IsEmpty()) return Reject(TEXT("Playable profile requires explicit ability presentations."));
        if (bPlayable && !WeaponMesh.LoadSynchronous()) return Reject(TEXT("Playable profile requires its authored weapon."));
        if (bPlayable && AnimationStyle == TEXT("shield") && !ShieldMesh.LoadSynchronous()) return Reject(TEXT("Sword-and-shield profile requires its authored shield."));
        for (const auto& Entry : AbilityPresentations)
        {
            const auto& Recipe = Entry.Value;
            if (!Entry.Key.ToString().StartsWith(ClassId.ToString()+TEXT(".")) || Recipe.VariantRoles.IsEmpty() || Recipe.SuppliedSources.IsEmpty()
                || !FMath::IsFinite(Recipe.Duration) || !FMath::IsFinite(Recipe.ContactSeconds)
                || Recipe.ContactSeconds <= 0 || Recipe.ContactSeconds >= Recipe.Duration)
                return Reject(TEXT("Ability presentation has invalid identity or event timing."));
            if (Recipe.Movement == TEXT("leap"))
            {
                if (Recipe.CapsuleHeights.Num() < 2 || !FMath::IsNearlyZero(Recipe.CapsuleHeights[0]) || !FMath::IsNearlyZero(Recipe.CapsuleHeights.Last()))
                    return Reject(TEXT("Leap movement requires a grounded start and recovery."));
                for (float Height : Recipe.CapsuleHeights)
                    if (!FMath::IsFinite(Height) || Height < 0 || Height > 150)
                        return Reject(TEXT("Leap capsule movement is invalid."));
            }
            for (FName Variant : Recipe.VariantRoles)
            {
                const auto* Ref = ImportedAnimations.Find(Variant);
                const auto* Sequence = Ref ? Ref->LoadSynchronous() : nullptr;
                if (!Sequence || FMath::Abs(Sequence->GetPlayLength()-Recipe.Duration) > 1.f/30.f)
                    return Reject(TEXT("Ability variants must exist and share the same gameplay duration."));
            }
        }
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
