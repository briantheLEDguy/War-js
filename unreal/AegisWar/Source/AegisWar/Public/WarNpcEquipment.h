#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "WarNpcEquipment.generated.h"

class USkeletalMesh;
class USkeletalMeshComponent;
class UStaticMesh;
class UActorComponent;

USTRUCT(BlueprintType)
struct FWarNpcWeaponAttachment
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere) FName Id;
    UPROPERTY(EditAnywhere) FName Bone;
    UPROPERTY(EditAnywhere) TSoftObjectPtr<UStaticMesh> Mesh;
    UPROPERTY(EditAnywhere) FTransform RelativeTransform;
    UPROPERTY(EditAnywhere) FString SourceSha256;
};

/** An exact body/loadout binding; a role alone cannot admit an arbitrary weapon. */
USTRUCT(BlueprintType)
struct FWarNpcLoadout
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere) FName Profile;
    UPROPERTY(EditAnywhere) FName Role;
    UPROPERTY(EditAnywhere) TArray<FName> Identities;
    UPROPERTY(EditAnywhere) TSoftObjectPtr<USkeletalMesh> Body;
    UPROPERTY(EditAnywhere) FString BodySourceSha256;
    UPROPERTY(EditAnywhere) TArray<FWarNpcWeaponAttachment> Attachments;
    UPROPERTY(EditAnywhere) TArray<FName> EmbeddedWeaponMaterialSlots;
};

UCLASS(BlueprintType)
class AEGISWAR_API UWarNpcEquipmentCatalog : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere) TArray<FWarNpcLoadout> Loadouts;
    bool Resolve(FName Profile, FName Identity, FName Role, const FWarNpcLoadout*& Out, FString& Error) const;
};

UCLASS()
class AEGISWAR_API UWarNpcEquipmentLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    static bool RequiresWeapons(FName Role);
    UFUNCTION(BlueprintPure, Category="NPC Equipment")
    static bool IsGeneratedAttachment(const UActorComponent* Component);
    /** Transient components follow skeletal bones and leave authored level packages untouched. */
    UFUNCTION(BlueprintCallable, Category="NPC Equipment")
    static bool Apply(USkeletalMeshComponent* Body, FName Profile, FName Identity, FName Role, FString& Error);
};
