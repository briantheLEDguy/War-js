#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarInterfaceProof.generated.h"

class FJsonObject;

/** Opt-in development smoke test; never created in shipping or ordinary gameplay. */
UCLASS()
class AEGISWAR_API UWarInterfaceProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
private:
    void Finish(bool Passed, const FString& Detail);
    void TickWorldBuilder(double Now);
    void TickWorldBuilderOrdinary(double Now);
    bool LoadOrdinaryBuilderConfig(FString& Error);
    bool CheckOrdinaryBuilderBindings(FString& Error) const;
    bool CheckOrdinaryBuilderSentinel(FString& Error) const;
    void FinishOrdinaryBuilder(bool Passed, const FString& Detail);
    void TickGmRendering(double Now);
    void TickTargeting(double Now);
    void TickCombatUi(double Now);
    TWeakObjectPtr<AActor> FriendlyTarget;
    TWeakObjectPtr<AActor> EnemyTarget;
    FVector BuilderStart;
    FName BuilderTemplate;
    int32 BuilderObjectCount = 0;
    int32 Step = 0;
    double NextStep = 0;
    bool bFinished = false;
    TSharedPtr<FJsonObject> OrdinaryBuilderConfig, OrdinaryBuilderManifest;
    FString OrdinaryBuilderConfigPath, OrdinaryBuilderConfigHash, OrdinaryBuilderOutput;
    FString OrdinaryBuilderRun, OrdinaryBuilderPhase, OrdinaryBuilderManifestHash;
    FString OrdinaryBuilderDraftHash, OrdinaryBuilderPublicationHash;
    TSet<FName> OrdinaryBuilderInitialIds;
    double OrdinaryBuilderStarted = 0;
    bool bOrdinaryBuilderGuiOpened = false;
    bool bOrdinaryBuilderSaveClicked = false;
    bool bOrdinaryBuilderLoadClicked = false;
    bool bOrdinaryBuilderPublishClicked = false;
    bool bOrdinaryBuilderStartupRestored = false;
    bool bOrdinaryBuilderConfigReady = false;
};
