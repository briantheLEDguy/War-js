#pragma once
#include "CoreMinimal.h"
#include "Animation/SkeletalMeshActor.h"
#include "WarCityNpc.generated.h"
class UTextRenderComponent;

UCLASS()
class AEGISWAR_API AWarCityNpc : public ASkeletalMeshActor
{
    GENERATED_BODY()
public:
    AWarCityNpc();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaTime) override;
    UPROPERTY(EditAnywhere, Category="City") FName NpcId;
    UPROPERTY(EditAnywhere, Category="City") FString DisplayName;
    UPROPERTY(EditAnywhere, Category="City") FName CityRole;
    UPROPERTY(EditAnywhere, Category="City") FName CharacterProfile;
    FName GetService() const;
    bool CanInteract(const APawn* Pawn) const;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<UTextRenderComponent> Nameplate;
};
