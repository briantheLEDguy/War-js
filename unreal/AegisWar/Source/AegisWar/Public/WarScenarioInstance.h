#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Tickable.h"
#include "Dom/JsonObject.h"
#include "WarSiegeRules.h"
#include "WarScenarioInstance.generated.h"
class AWarPlayerController;
class AWarSiegeBattlefield;
namespace WarScenarioCandidateProof
{
    AEGISWAR_API bool Identity(const TSharedPtr<FJsonObject>& Proof,FString& Error);
    AEGISWAR_API bool LoopbackUrl(const FString& Url);
    AEGISWAR_API bool Bindings(const TSharedPtr<FJsonObject>& Proof,FString& Error);
    AEGISWAR_API bool Battlefield(const TSharedPtr<FJsonObject>& Proof,const AWarSiegeBattlefield* Field,FString& Error,
        const TSharedPtr<FJsonObject>& Blueprint=nullptr);
}
UCLASS()
class AEGISWAR_API UWarScenarioInstance : public UGameInstanceSubsystem, public FTickableGameObject
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Tick(float Delta) override;
    virtual bool IsTickable() const override { return !IsTemplate() && Config.IsValid(); }
    virtual TStatId GetStatId() const override;
    bool IsEnabled() const { return Config.IsValid(); }
    bool AllowsLan() const;
    int32 RulesVersion() const;
    int32 Capacity() const;
    EWarSiegeScenario Scenario() const;
    FString ContentRevision() const;
    bool ReviewCandidate(AWarSiegeBattlefield* Field,FString& Error,bool Recheck=false);
    bool Owns(AWarPlayerController* PC) const { return !IsEnabled() || (!bFinished && Players.Contains(PC)); }
    bool CanStart(int32 Humans) const;
    void Admit(const FString& Ticket,TFunction<void(FString)> Complete);
    bool Attach(AWarPlayerController* PC,const FString& Ticket,FString& Error);
    void Disconnect(AWarPlayerController* PC);
    void Finish();
private:
    void Send(const FString& Path,TSharedPtr<FJsonObject> Body,TFunction<void(bool,TSharedPtr<FJsonObject>,FString)> Reply);
    TSharedPtr<FJsonObject> Config;
    TSharedPtr<FJsonObject> CandidateProof;
    TSharedPtr<FJsonObject> CandidateBlueprint;
    FString CandidateError;
    TMap<FString,TSharedPtr<FJsonObject>> Pending;
    TMap<FString,double> PendingAt;
    TSet<FString> InFlight;
    TMap<TWeakObjectPtr<AWarPlayerController>,FString> Players;
    TSharedPtr<FJsonObject> Roster;
    double NextPoll=0,FirstPlayerAt=0,LastHeartbeat=0;
    bool bPolling=false,bFinished=false;
};
