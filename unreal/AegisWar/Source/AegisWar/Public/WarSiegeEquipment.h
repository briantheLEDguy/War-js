#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GameFramework/Actor.h"
#include "WarSiegeEquipment.generated.h"
class UStaticMesh;
class UStaticMeshComponent;
class UAnimSequence;
class AWarSiegeCharacter;
class AWarCharacter;
class ANavigationData;

namespace WarSiegeEquipment
{
    AEGISWAR_API FRotator SurfaceRotation(float Yaw, float ForwardGrade, float RightGrade);
    AEGISWAR_API ANavigationData* Navigation(UWorld* World);
    AEGISWAR_API FVector TrailingPoint(TConstArrayView<FVector> Trail, float Distance);
}

USTRUCT(BlueprintType)
struct FWarSiegeEquipmentPart
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere) TSoftObjectPtr<UStaticMesh> Mesh;
    // Sampled from the retained authored mechanical clips, relative to their rest geometry.
    UPROPERTY(EditAnywhere) TArray<FTransform> Roll;
    UPROPERTY(EditAnywhere) TArray<FTransform> Strike;
};

UCLASS(BlueprintType)
class AEGISWAR_API UWarSiegeEquipmentDefinition : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere) TArray<FWarSiegeEquipmentPart> Parts;
    UPROPERTY(EditAnywhere) FVector HullExtent = FVector(240,175,120);
    UPROPERTY(EditAnywhere) TArray<FVector> CrewPositions;
    UPROPERTY(EditAnywhere) TSoftObjectPtr<UAnimSequence> PushAnimation;
    UPROPERTY(EditAnywhere) TSoftObjectPtr<UAnimSequence> HoldAnimation;
    UPROPERTY(EditAnywhere) float WalkSpeed = 100;
    UPROPERTY(EditAnywhere) float WheelCircumference = 485;
    UPROPERTY(EditAnywhere) float StrikeDuration = 1.5f;
    UPROPERTY(EditAnywhere) bool bBatteringRam = false;
    UPROPERTY(EditAnywhere) FString SourceSha256;
    UPROPERTY(EditAnywhere) bool bReviewed = false;
    bool Validate(FString& Error) const;
};

/** Authoritative swept convoy; replicated distance drives wheel and crew motion. */
UCLASS()
class AEGISWAR_API AWarSiegeEquipment : public AActor
{
    GENERATED_BODY()
public:
    AWarSiegeEquipment();
    UPROPERTY(ReplicatedUsing=OnRep_Definition) TObjectPtr<UWarSiegeEquipmentDefinition> Definition;
    UPROPERTY(Replicated) TArray<TObjectPtr<AWarSiegeCharacter>> Engineers;
    UPROPERTY(Replicated) float Travel = 0;
    UPROPERTY(Replicated) bool bMoving = false;
    UPROPERTY(Replicated) double StrikeStarted = -1;
    bool Initialize(UWarSiegeEquipmentDefinition* InDefinition);
    bool TryPlace();
    bool IsPlaced() const { return bPlaced; }
    bool MovementClear(const FVector& Position, const FRotator& Rotation) const;
    bool PoseClear(const FVector& Position, const FQuat& Rotation, float Margin = 0) const;
    bool HasCrew() const;
    FVector CrewPosition(int32 Seat) const;
    FVector TrailingLocation(float Distance) const;
    bool BindEngineer(int32 Seat, AWarSiegeCharacter* Engineer);
    bool Drive(const FVector& Destination, float Speed, float Delta);
    void Stop();
    void Operate(bool bEnabled);
    bool CrewAnimation(UAnimSequence*& Clip, float& Time) const;
    virtual void Tick(float Delta) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
private:
    UFUNCTION() void OnRep_Definition();
    UFUNCTION() void OnRep_Placed();
    UPROPERTY(ReplicatedUsing=OnRep_Placed) bool bPlaced = false;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Meshes;
    UPROPERTY() TObjectPtr<class UBoxComponent> Hull;
    TArray<FVector> Route;
    FVector RouteGoal = FVector::ZeroVector;
    TArray<FVector> Trail;
    float TrailLength=0;
    bool Ground(const FVector& At, FVector& Result) const;
    bool GroundPose(FVector& Position, FRotator& Rotation) const;
    bool RecoverOverlaps();
    void UpdateEscapeCollision();
    TSet<TWeakObjectPtr<AWarCharacter>> EscapingPawns;
    void PlaceEngineers();
};
