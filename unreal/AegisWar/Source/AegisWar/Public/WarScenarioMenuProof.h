#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Tickable.h"
#include "Dom/JsonObject.h"
#include "WarScenarioMenuProof.generated.h"

/** Opt-in rendered menu/travel/return fixture; never enables gameplay or admission. */
UCLASS()
class UWarScenarioMenuProof : public UGameInstanceSubsystem, public FTickableGameObject
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool IsTickable() const override { return !IsTemplate() && !Finished; }
    virtual void Tick(float Delta) override;
    virtual TStatId GetStatId() const override;
private:
    void Finish(bool Passed,const FString& Detail);
    void Capture(const FString& Name);
    bool LoadCandidate(FString& Error);
    bool ObserveCandidate(FString& Error);
    int32 Step=0, Side=0, ConnectionStep=0;
    double Started=0, Next=0;
    bool Finished=false,PartyInvited=false,OptionalChecked=false;
    FVector CampaignPosition=FVector::ZeroVector,BeforeMove=FVector::ZeroVector,OrderAnchor=FVector::ZeroVector;
    FString CampaignInventory,PartyRole;
    FString CandidatePath,CandidateHash;
    TSharedPtr<FJsonObject> CandidateProof,CandidateBlueprint,CandidateWitness;
    bool CandidateNormalized=false,CandidateReturned=false;
    TMap<TWeakObjectPtr<AActor>,FVector> BotPositions;
};
