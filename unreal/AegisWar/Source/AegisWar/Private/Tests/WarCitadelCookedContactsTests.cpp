#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarCitadelCookedContacts.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelCookedBoundsTest,"AegisWar.Foundation.CitadelCookedAffineBounds",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCitadelCookedBoundsTest::RunTest(const FString& Parameters)
{
    const FTransform Wrapper(FRotator(0,90,0),FVector(13296,-6788,4349),FVector(.90416663885,1,1));
    const FTransform Parent(FRotator(18,31,7),FVector(100,-250,200),FVector(2,3,.75));
    const FVector Probe(123,-456,789);
    const FMatrix Composed=Wrapper.ToMatrixWithScale()*Parent.ToMatrixWithScale();
    TestTrue(TEXT("Matrix composition matches independently applied child then parent wrappers"),
        FVector(Composed.TransformPosition(Probe)).Equals(Parent.TransformPosition(Wrapper.TransformPosition(Probe)),1.e-8));
    const FBox World(FVector(12000,-7100,4100),FVector(12100,-7000,4300));
    for (const FMatrix& Frame:{Wrapper.ToMatrixWithScale(),Wrapper.ToMatrixWithScale()*Parent.ToMatrixWithScale()})
    {
        FBox Local;double Error=0;
        TestTrue(TEXT("Rotated nonuniform and sheared compositions retain an exact conservative inverse"),
            WarCitadelCookedContacts::ConservativeLocalBounds(Frame,World,Local,Error));
        TestTrue(TEXT("All bounds roundtrips remain below numerical diagnostic precision"),Error<1.e-6);
        for (int32 I=0;I<8;++I)
        {
            const FVector Corner((I&1)?World.Max.X:World.Min.X,(I&2)?World.Max.Y:World.Min.Y,(I&4)?World.Max.Z:World.Min.Z);
            const FVector Expected(Frame.Inverse().TransformPosition(Corner));
            TestTrue(TEXT("Every inverse-transformed corner is included in the local candidate AABB"),Local.IsInsideOrOn(Expected));
            TestTrue(TEXT("The composed forward map preserves each world-space corner"),
                FVector(Frame.TransformPosition(Expected)).Equals(Corner,1.e-6));
        }
    }
    FBox Local;double Error=0;
    TestTrue(TEXT("Single TRS inverse agrees with inverse-transform-position under ninety-degree nonuniform scale"),
        WarCitadelCookedContacts::ConservativeLocalBounds(Wrapper.ToMatrixWithScale(),World,Local,Error));
    const FVector Correct=Wrapper.InverseTransformPosition(World.Min);
    const FVector Incorrect=Wrapper.Inverse().TransformPosition(World.Min);
    TestTrue(TEXT("Control detects the lossy FTransform inverse order"),FVector::Distance(Correct,Incorrect)>1.);
    const FVector MatrixInverse(Wrapper.ToMatrixWithScale().Inverse().TransformPosition(World.Min));
    TestTrue(TEXT("Exact matrix agrees with inverse-position control within floating-point precision"),MatrixInverse.Equals(Correct,1.e-8));
    TestTrue(TEXT("Exact candidate bounds contain their inverse-matrix corner"),Local.IsInsideOrOn(MatrixInverse));
    TestFalse(TEXT("Singular wrappers cannot claim complete geometry coverage"),
        WarCitadelCookedContacts::ConservativeLocalBounds(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(0,1,1)).ToMatrixWithScale(),World,Local,Error));
    TestFalse(TEXT("Invalid bounds cannot claim complete geometry coverage"),
        WarCitadelCookedContacts::ConservativeLocalBounds(FMatrix::Identity,FBox(ForceInit),Local,Error));
    return true;
}
#endif
