#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarFrontendProof.generated.h"

/** Explicit rendered fixture, following ordinary no-pawn login startup. */
UCLASS()
class AEGISWAR_API UWarFrontendProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override { return Type == EWorldType::Game; }
    virtual void Tick(float Delta) override;
    virtual TStatId GetStatId() const override;
private:
    void Finish(bool Passed, const FString& Detail);
    int32 Step = 0;
    double Started = 0, Next = 0;
    bool bFinished = false;
    TArray<float> FrameTimes;
    TArray<float> SteadyFrameTimes;
    TArray<float> FadeFrameTimes;
    TFunction<void(class UWarFrontendWidget*)> AfterScreenshot;
};
